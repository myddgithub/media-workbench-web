from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class MediaRoot:
    key: str
    label: str
    path: Path


@dataclass(frozen=True)
class Settings:
    roots: dict[str, MediaRoot]
    state_dir: Path
    database_path: Path
    ffmpeg: str
    ffprobe: str
    poll_seconds: float
    app_title: str
    deployment: str  # "nas" | "local"


def _root_key(label: str) -> str:
    key = re.sub(r"[^A-Za-z0-9_-]+", "-", label.strip()).strip("-")
    return key or "root"


def parse_media_roots(raw: str | None) -> dict[str, MediaRoot]:
    """Parse ``label=/container/path;other=/path`` into configured roots."""
    raw = (raw or "Mydata=/data/mydata").strip()
    roots: dict[str, MediaRoot] = {}
    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"MEDIA_ROOTS 项缺少 '=': {item}")
        label, path_text = (part.strip() for part in item.split("=", 1))
        if not label or not path_text:
            raise ValueError(f"MEDIA_ROOTS 项无效: {item}")
        key = _root_key(label)
        suffix = 2
        original = key
        while key in roots:
            key = f"{original}-{suffix}"
            suffix += 1
        roots[key] = MediaRoot(key=key, label=label, path=Path(path_text))
    if not roots:
        raise ValueError("至少需要配置一个 MEDIA_ROOTS 路径")
    return roots


def _parse_deployment(raw: str | None) -> str:
    value = (raw or "nas").strip().lower()
    if value in ("local", "desktop", "win", "windows"):
        return "local"
    return "nas"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    state_dir = Path(os.getenv("STATE_DIR", "/state"))
    return Settings(
        roots=parse_media_roots(os.getenv("MEDIA_ROOTS")),
        state_dir=state_dir,
        database_path=Path(os.getenv("DATABASE_PATH", str(state_dir / "jobs.sqlite3"))),
        ffmpeg=os.getenv("FFMPEG_BIN", "ffmpeg"),
        ffprobe=os.getenv("FFPROBE_BIN", "ffprobe"),
        poll_seconds=max(0.2, float(os.getenv("JOB_POLL_SECONDS", "1"))),
        app_title=os.getenv("APP_TITLE", "音视频与 TextGrid 处理工作台"),
        deployment=_parse_deployment(os.getenv("DEPLOYMENT")),
    )
