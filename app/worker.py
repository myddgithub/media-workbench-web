from __future__ import annotations

import signal
import time
import traceback

from .config import get_settings
from .dispatcher import execute
from .media import TaskCancelled
from .paths import PathResolver
from .store import JobStore


def main() -> None:
    settings = get_settings()
    store = JobStore(settings.database_path)
    resolver = PathResolver(settings.roots)
    stopping = False

    def stop(*_args):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    interrupted = store.recover_interrupted()
    if interrupted:
        print(f"Marked {interrupted} interrupted job(s) as failed", flush=True)
    print("Media workbench worker started", flush=True)

    while not stopping:
        store.touch_worker()
        job = store.claim_next()
        if not job:
            time.sleep(settings.poll_seconds)
            continue
        job_id = job["id"]
        store.append_log(job_id, f"开始执行 {job['kind']} 任务")
        try:
            result = execute(
                job["kind"],
                job["payload"],
                settings=settings,
                resolver=resolver,
                progress=lambda value, message: store.progress(job_id, value, message),
                log=lambda line: store.append_log(job_id, line),
                cancelled=lambda: stopping or store.is_cancel_requested(job_id),
            )
            if stopping or store.is_cancel_requested(job_id):
                raise TaskCancelled("任务已取消")
            store.append_log(job_id, result.get("summary", "任务完成"))
            store.complete(job_id, result)
        except TaskCancelled:
            store.append_log(job_id, "任务已取消；未完成的临时输出已清理")
            store.mark_cancelled(job_id)
        except Exception as exc:
            store.append_log(job_id, f"任务失败：{exc}")
            store.append_log(job_id, traceback.format_exc())
            store.fail(job_id, str(exc))
        finally:
            store.touch_worker()

    print("Media workbench worker stopped", flush=True)


if __name__ == "__main__":
    main()
