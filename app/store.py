from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TERMINAL_STATES = {"succeeded", "failed", "cancelled"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStore:
    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path, timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _initialize(self) -> None:
        with self._init_lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    result TEXT,
                    progress REAL NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '',
                    logs TEXT NOT NULL DEFAULT '',
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_status_created
                    ON jobs(status, created_at);
                CREATE TABLE IF NOT EXISTS runtime (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        item["result"] = json.loads(item["result"]) if item["result"] else None
        item["cancel_requested"] = bool(item["cancel_requested"])
        return item

    def create(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO jobs
                   (id, kind, status, payload, created_at, updated_at)
                   VALUES (?, ?, 'queued', ?, ?, ?)""",
                (job_id, kind, json.dumps(payload, ensure_ascii=False), now, now),
            )
        return self.get(job_id)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._decode(row)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._decode(row) for row in rows]

    def claim_next(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT id FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                conn.execute("COMMIT")
                return None
            now = utc_now()
            conn.execute(
                """UPDATE jobs SET status='running', started_at=?, updated_at=?,
                   message='任务开始执行' WHERE id=? AND status='queued'""",
                (now, now, row["id"]),
            )
            conn.execute("COMMIT")
        return self.get(row["id"])

    def progress(self, job_id: str, value: float, message: str = "") -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """UPDATE jobs SET progress=?, message=?, updated_at=?
                   WHERE id=? AND status IN ('running','cancelling')""",
                (max(0.0, min(float(value), 1.0)), message[:500], now, job_id),
            )

    def append_log(self, job_id: str, line: str) -> None:
        line = str(line).rstrip()
        if not line:
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        with self._connect() as conn:
            row = conn.execute("SELECT logs FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                return
            logs = (row["logs"] + f"[{stamp}] {line}\n")[-120_000:]
            conn.execute(
                "UPDATE jobs SET logs=?, updated_at=? WHERE id=?",
                (logs, utc_now(), job_id),
            )

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """UPDATE jobs SET status='succeeded', progress=1, message='任务完成',
                   result=?, finished_at=?, updated_at=? WHERE id=?""",
                (json.dumps(result, ensure_ascii=False), now, now, job_id),
            )

    def fail(self, job_id: str, message: str) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """UPDATE jobs SET status='failed', message=?, finished_at=?, updated_at=?
                   WHERE id=?""",
                (message[:1000], now, now, job_id),
            )

    def mark_cancelled(self, job_id: str) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """UPDATE jobs SET status='cancelled', message='任务已取消',
                   finished_at=?, updated_at=? WHERE id=?""",
                (now, now, job_id),
            )

    def request_cancel(self, job_id: str) -> dict[str, Any] | None:
        job = self.get(job_id)
        if not job or job["status"] in TERMINAL_STATES:
            return job
        now = utc_now()
        with self._connect() as conn:
            if job["status"] == "queued":
                conn.execute(
                    """UPDATE jobs SET status='cancelled', cancel_requested=1,
                       message='任务已取消', finished_at=?, updated_at=? WHERE id=?""",
                    (now, now, job_id),
                )
            else:
                conn.execute(
                    """UPDATE jobs SET status='cancelling', cancel_requested=1,
                       message='正在停止任务', updated_at=? WHERE id=?""",
                    (now, job_id),
                )
        return self.get(job_id)

    def is_cancel_requested(self, job_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT cancel_requested FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
        return bool(row and row[0])

    def delete(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job or job["status"] not in TERMINAL_STATES:
            return False
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        return cur.rowcount > 0

    def recover_interrupted(self) -> int:
        now = utc_now()
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE jobs SET status='failed', message='worker 重启，任务执行中断',
                   finished_at=?, updated_at=?
                   WHERE status IN ('running','cancelling')""",
                (now, now),
            )
        return cur.rowcount

    def touch_worker(self) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO runtime(key, value, updated_at) VALUES('worker','alive',?)
                   ON CONFLICT(key) DO UPDATE SET value='alive', updated_at=excluded.updated_at""",
                (now,),
            )

    def worker_state(self) -> dict[str, str] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runtime WHERE key='worker'").fetchone()
        return dict(row) if row else None
