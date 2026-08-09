from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .config import Settings
from .media import TaskCancelled, probe_duration, run_ffmpeg
from .paths import PathResolver


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"}

AUDIO_OUTPUTS = {
    "pcm_s16le": ".wav",
    "libmp3lame": ".mp3",
    "aac": ".m4a",
    "flac": ".flac",
    "libvorbis": ".ogg",
    "libopus": ".opus",
}


def matches_mode(path: Path, mode: str) -> bool:
    suffix = path.suffix.lower()
    if mode == "video_to_audio":
        return suffix in VIDEO_EXTENSIONS
    if mode == "audio_to_audio":
        return suffix in AUDIO_EXTENSIONS
    return suffix in VIDEO_EXTENSIONS


def scan_conversion_files(path: Path, mode: str, recursive: bool = True) -> list[Path]:
    if path.is_file():
        return [path] if matches_mode(path, mode) else []
    iterator = path.rglob("*") if recursive else path.iterdir()
    return sorted(
        (item for item in iterator if item.is_file() and matches_mode(item, mode)),
        key=lambda item: str(item).casefold(),
    )


def output_extension(payload: dict[str, Any]) -> str:
    if payload["mode"] in ("video_to_audio", "audio_to_audio"):
        return AUDIO_OUTPUTS[payload["audio_codec"]]
    return payload["video_format"]


def build_conversion_arguments(input_path: Path, payload: dict[str, Any]) -> list[str]:
    mode = payload["mode"]
    args = ["-hide_banner", "-y", "-i", str(input_path)]
    if mode in ("video_to_audio", "audio_to_audio"):
        if mode == "video_to_audio":
            args += ["-vn"]
        codec = payload["audio_codec"]
        args += [
            "-c:a", codec,
            "-ar", str(payload["sample_rate"]),
            "-ac", str(payload["channels"]),
        ]
        if codec not in {"pcm_s16le", "flac"}:
            args += ["-b:a", payload["audio_bitrate"]]
        if codec == "pcm_s16le":
            args += ["-sample_fmt", "s16"]
        if mode == "audio_to_audio":
            args += ["-map_metadata", "-1"]
        return args

    resolution = payload.get("resolution", "").strip().lower().replace("x", ":")
    if resolution:
        args += ["-vf", f"scale={resolution}"]
    codec = payload["video_codec"]
    args += ["-c:v", codec]
    if codec in {"h264_qsv", "hevc_qsv"}:
        args += ["-global_quality", str(payload["crf"]), "-look_ahead", "0"]
    elif codec == "libvpx-vp9":
        args += ["-crf", str(payload["crf"]), "-b:v", "0"]
    elif codec == "mpeg4":
        args += ["-q:v", str(max(1, min(31, round(payload["crf"] / 2))))]
    else:
        args += ["-preset", payload["preset"], "-crf", str(payload["crf"])]
    args += ["-pix_fmt", "yuv420p"]
    if payload["video_format"] == ".webm":
        args += ["-c:a", "libopus", "-b:a", "128k"]
    else:
        args += ["-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart"]
    if mode == "compress":
        args += ["-map_chapters", "-1"]
    return args


def execute_conversion(
    payload: dict[str, Any],
    *,
    settings: Settings,
    resolver: PathResolver,
    progress,
    log,
    cancelled,
) -> dict[str, Any]:
    source = resolver.resolve(payload["input_root"], payload["input_path"])
    destination = resolver.resolve(
        payload["output_root"], payload["output_path"], must_exist=False
    )
    destination.mkdir(parents=True, exist_ok=True)
    files = scan_conversion_files(source, payload["mode"], payload["recursive"])
    if not files:
        raise ValueError("所选路径中没有与转换模式匹配的媒体文件")

    source_base = source if source.is_dir() else source.parent
    extension = output_extension(payload)
    outputs: list[dict[str, str]] = []
    skipped: list[str] = []
    completed = 0
    fractions = {index: 0.0 for index in range(len(files))}
    lock = threading.Lock()

    def report(index: int, fraction: float, name: str) -> None:
        with lock:
            fractions[index] = fraction
            overall = sum(fractions.values()) / len(files)
        progress(overall, f"正在转换：{name}")

    def convert_one(index: int, input_file: Path):
        nonlocal completed
        if cancelled():
            raise TaskCancelled("任务已取消")
        relative_parent = input_file.parent.relative_to(source_base) if source.is_dir() else Path()
        output = destination / relative_parent / f"{input_file.stem}{extension}"
        if output.resolve(strict=False) == input_file.resolve(strict=False):
            output = output.with_name(f"{output.stem}_converted{output.suffix}")
        if output.exists() and not payload["overwrite"]:
            log(f"跳过已存在文件：{output.name}")
            with lock:
                skipped.append(resolver.relative(payload["output_root"], output))
            report(index, 1, output.name)
            return
        log(f"转换：{input_file.name} → {output.name}")
        duration = probe_duration(settings.ffprobe, input_file)
        run_ffmpeg(
            settings.ffmpeg,
            build_conversion_arguments(input_file, payload),
            output,
            duration=duration,
            progress=lambda value, name: report(index, value, name),
            log=log,
            cancelled=cancelled,
        )
        with lock:
            outputs.append(
                {"root": payload["output_root"], "path": resolver.relative(payload["output_root"], output)}
            )
            completed += 1

    with ThreadPoolExecutor(max_workers=payload["workers"]) as executor:
        futures = [executor.submit(convert_one, i, path) for i, path in enumerate(files)]
        for future in as_completed(futures):
            future.result()

    return {
        "summary": f"转换完成 {completed} 个，跳过 {len(skipped)} 个",
        "files": sorted(outputs, key=lambda item: item["path"].casefold()),
        "skipped": skipped,
    }
