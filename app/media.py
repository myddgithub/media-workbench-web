from __future__ import annotations

import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Callable


ProgressCallback = Callable[[float, str], None]
LogCallback = Callable[[str], None]
CancelCallback = Callable[[], bool]


class TaskCancelled(RuntimeError):
    pass


def probe_duration(ffprobe: str, path: Path) -> float:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"无法读取媒体时长 {path.name}: {result.stderr.strip()}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"媒体时长无效: {path.name}") from exc


def _temporary_output(output: Path) -> Path:
    return output.with_name(f".{output.stem}.{uuid.uuid4().hex[:8]}.work{output.suffix}")


def run_ffmpeg(
    ffmpeg: str,
    arguments: list[str],
    output: Path,
    *,
    duration: float = 0,
    progress: ProgressCallback | None = None,
    log: LogCallback | None = None,
    cancelled: CancelCallback | None = None,
) -> None:
    """Run FFmpeg into a temporary file and publish it atomically on success."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_output(output)
    command = [ffmpeg, *arguments, "-progress", "pipe:1", "-nostats", str(temporary)]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    errors: list[str] = []
    try:
        assert process.stdout is not None
        for raw in process.stdout:
            if cancelled and cancelled():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise TaskCancelled("任务已取消")
            line = raw.strip()
            if not line:
                continue
            if line.startswith(("out_time_ms=", "out_time_us=")) and duration > 0:
                try:
                    elapsed = int(line.split("=", 1)[1]) / 1_000_000
                    if progress:
                        progress(min(elapsed / duration, 0.995), output.name)
                except (ValueError, ZeroDivisionError):
                    pass
                continue
            if line.startswith("progress="):
                continue
            lowered = line.lower()
            if any(word in lowered for word in ("error", "invalid", "failed", "cannot")):
                errors.append(line)
            if log and (line.startswith("frame=") or errors and errors[-1] == line):
                log(line)
        return_code = process.wait()
        if return_code != 0:
            detail = "\n".join(errors[-8:]) or f"FFmpeg 退出码 {return_code}"
            raise RuntimeError(detail)
        os.replace(temporary, output)
        if progress:
            progress(1.0, output.name)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def atomic_write_textgrid(textgrid, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_output(output)
    try:
        textgrid.write(str(temporary))
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def wait_or_cancel(seconds: float, cancelled: CancelCallback | None = None) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if cancelled and cancelled():
            raise TaskCancelled("任务已取消")
        time.sleep(min(0.1, end - time.monotonic()))
