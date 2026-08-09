from __future__ import annotations

import re
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .config import Settings
from .media import TaskCancelled, probe_duration, run_ffmpeg
from .paths import PathResolver
from .textgrid_ops import (
    calculate_segments,
    read_textgrid,
    semantic_intervals,
    write_clipped_textgrid,
    write_merged_textgrid,
)


@dataclass
class SourceSet:
    base: str
    audio: Path | None = None
    video: Path | None = None
    textgrid: Path | None = None


SUPPORTED = {".wav": "audio", ".mp4": "video", ".textgrid": "textgrid"}
SEGMENT_RE = re.compile(r"^(?P<prefix>.+)_seg(?P<index>\d+)$", re.IGNORECASE)


def discover_source_sets(directory: Path) -> dict[str, SourceSet]:
    groups: dict[str, SourceSet] = {}
    for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file():
            continue
        media_type = SUPPORTED.get(path.suffix.lower())
        if not media_type:
            continue
        key = path.stem.casefold()
        group = groups.setdefault(key, SourceSet(base=path.stem))
        setattr(group, media_type, path)
    return groups


def scan_cme(directory: Path) -> dict[str, Any]:
    groups = discover_source_sets(directory)
    prefixes = sorted(
        {
            match.group("prefix")
            for group in groups.values()
            if (match := SEGMENT_RE.match(group.base))
        },
        key=str.casefold,
    )
    regular = [group for group in groups.values() if not SEGMENT_RE.match(group.base)]
    return {
        "groups": len(regular),
        "segments": len(groups) - len(regular),
        "prefixes": prefixes,
        "items": [
            {
                "base": group.base,
                "audio": bool(group.audio),
                "video": bool(group.video),
                "textgrid": bool(group.textgrid),
            }
            for group in regular[:500]
        ],
    }


def _enabled(content: dict[str, bool]) -> list[str]:
    return [name for name in ("audio", "video", "textgrid") if content.get(name)]


def _group_duration(group: SourceSet, content: dict[str, bool], settings: Settings) -> float:
    if content.get("video") and group.video:
        return probe_duration(settings.ffprobe, group.video)
    if content.get("audio") and group.audio:
        return probe_duration(settings.ffprobe, group.audio)
    if content.get("textgrid") and group.textgrid:
        return float(read_textgrid(group.textgrid).maxTime)
    return 0.0


def _merge_group_duration(group: SourceSet, content: dict[str, bool], settings: Settings) -> float:
    """CME merge rule: TextGrid duration first, then video, then audio."""
    if content.get("textgrid") and group.textgrid:
        grid = read_textgrid(group.textgrid)
        return float(grid.maxTime) - float(grid.minTime)
    if content.get("video") and group.video:
        return probe_duration(settings.ffprobe, group.video)
    if content.get("audio") and group.audio:
        return probe_duration(settings.ffprobe, group.audio)
    return 0.0


def _video_trim_arguments(source: Path, start: float, duration: float) -> list[str]:
    return [
        "-hide_banner", "-y", "-i", str(source),
        "-ss", f"{start:.9f}", "-t", f"{duration:.9f}",
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart",
    ]


def _audio_trim_arguments(source: Path, start: float, duration: float) -> list[str]:
    return [
        "-hide_banner", "-y", "-i", str(source),
        "-ss", f"{start:.9f}", "-t", f"{duration:.9f}",
        "-c:a", "pcm_s16le",
    ]


def _result(root: str, resolver: PathResolver, path: Path) -> dict[str, str]:
    return {"root": root, "path": resolver.relative(root, path)}


def _should_write(path: Path, overwrite: bool, log) -> bool:
    if path.exists() and not overwrite:
        log(f"跳过已存在文件：{path.name}")
        return False
    return True


def _parallel_groups(
    items,
    workers: int,
    process: Callable[[int, Any, Callable[[float, str], None]], list[dict[str, str]]],
    progress,
) -> list[dict[str, str]]:
    items = list(items)
    fractions = {index: 0.0 for index in range(len(items))}
    results: list[dict[str, str]] = []
    lock = threading.Lock()

    def report(index: int, fraction: float, message: str):
        with lock:
            fractions[index] = max(fractions[index], min(1.0, fraction))
            overall = sum(fractions.values()) / max(1, len(items))
        progress(overall, message)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process, index, item, lambda f, m, i=index: report(i, f, m)): index
            for index, item in enumerate(items)
        }
        for future in as_completed(futures):
            outputs = future.result()
            with lock:
                results.extend(outputs)
            report(futures[future], 1.0, "已完成一个处理组")
    return results


def execute_cut(payload, *, settings, resolver, progress, log, cancelled):
    source_dir = resolver.resolve(payload["input_root"], payload["input_path"], kind="dir")
    output_dir = resolver.resolve(
        payload["output_root"], payload["output_path"], must_exist=False
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    groups = [
        group for group in discover_source_sets(source_dir).values()
        if not SEGMENT_RE.match(group.base)
    ]
    if not groups:
        raise ValueError("输入目录中没有可切分的 .mp4、.wav 或 .TextGrid 文件组")
    content = payload["content"]

    def process(index, group: SourceSet, report):
        if cancelled():
            raise TaskCancelled("任务已取消")
        total = _group_duration(group, content, settings)
        if total < 1:
            log(f"跳过 {group.base}：时长不足 1 秒")
            return []
        sg = []
        if payload["use_sg_align"] and content["textgrid"] and group.textgrid:
            sg = semantic_intervals(read_textgrid(group.textgrid))
            if sg:
                log(f"{group.base}：找到 {len(sg)} 个有效 SG 区间")
        segments = calculate_segments(total, payload["segment_length"], sg)
        if not segments:
            log(f"跳过 {group.base}：未产生有效片段")
            return []
        outputs = []
        enabled = _enabled(content)
        operation_count = max(1, len(segments) * len(enabled))
        operation = 0
        for segment_index, (start, end) in enumerate(segments):
            if cancelled():
                raise TaskCancelled("任务已取消")
            base = f"{group.base}_seg{segment_index:03d}"
            duration = end - start
            log(f"切分 {base}：{start:.3f}s–{end:.3f}s")
            for media_type in enabled:
                source = getattr(group, media_type)
                operation += 1
                if not source:
                    log(f"{group.base} 缺少 {media_type}，已跳过该项")
                    report(operation / operation_count, f"{base} 缺少文件")
                    continue
                suffix = {"audio": ".wav", "video": ".mp4", "textgrid": ".TextGrid"}[media_type]
                output = output_dir / f"{base}{suffix}"
                if not _should_write(output, payload["overwrite"], log):
                    report(operation / operation_count, f"跳过 {output.name}")
                    continue
                if media_type == "video":
                    run_ffmpeg(
                        settings.ffmpeg,
                        _video_trim_arguments(source, start, duration),
                        output,
                        duration=duration,
                        progress=lambda value, name, op=operation: report(
                            (op - 1 + value) / operation_count, f"正在切分 {name}"
                        ),
                        log=log,
                        cancelled=cancelled,
                    )
                elif media_type == "audio":
                    run_ffmpeg(
                        settings.ffmpeg,
                        _audio_trim_arguments(source, start, duration),
                        output,
                        duration=duration,
                        progress=lambda value, name, op=operation: report(
                            (op - 1 + value) / operation_count, f"正在切分 {name}"
                        ),
                        log=log,
                        cancelled=cancelled,
                    )
                else:
                    write_clipped_textgrid(source, output, start, end)
                outputs.append(_result(payload["output_root"], resolver, output))
                report(operation / operation_count, f"完成 {output.name}")
        return outputs

    files = _parallel_groups(groups, payload["workers"], process, progress)
    return {"summary": f"切分完成，共生成 {len(files)} 个文件", "files": files}


def _segment_groups(source_dir: Path, prefixes: list[str]) -> dict[str, list[tuple[int, SourceSet]]]:
    discovered = discover_source_sets(source_dir)
    requested = {prefix.casefold(): prefix for prefix in prefixes if prefix.strip()}
    groups: dict[str, list[tuple[int, SourceSet]]] = {}
    display: dict[str, str] = {}
    for source in discovered.values():
        match = SEGMENT_RE.match(source.base)
        if not match:
            continue
        prefix = match.group("prefix")
        key = prefix.casefold()
        if requested and key not in requested:
            continue
        display.setdefault(key, requested.get(key, prefix))
        groups.setdefault(key, []).append((int(match.group("index")), source))
    return {
        display[key]: sorted(items, key=lambda item: item[0])
        for key, items in sorted(groups.items(), key=lambda item: item[0])
    }


def _concat_file(paths: list[Path]) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="media-concat-", delete=False, encoding="utf-8"
    )
    with handle:
        for path in paths:
            escaped = str(path).replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")
    return Path(handle.name)


def _concat_arguments(list_file: Path, media_type: str) -> list[str]:
    args = ["-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file)]
    if media_type == "video":
        args += [
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-movflags", "+faststart",
        ]
    else:
        args += ["-c:a", "pcm_s16le"]
    return args


def execute_merge(payload, *, settings, resolver, progress, log, cancelled):
    source_dir = resolver.resolve(payload["input_root"], payload["input_path"], kind="dir")
    output_dir = resolver.resolve(
        payload["output_root"], payload["output_path"], must_exist=False
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    groups = _segment_groups(source_dir, payload["prefixes"])
    if not groups:
        raise ValueError("没有找到符合“前缀_segNNN”命名的待合并片段")
    content = payload["content"]

    def process(index, item, report):
        prefix, segments = item
        enabled = _enabled(content)
        log(f"开始合并 {prefix}，共 {len(segments)} 段")
        if payload["strict_triplets"]:
            missing = [
                f"{segment.base}.{media_type}"
                for _, segment in segments
                for media_type in enabled
                if not getattr(segment, media_type)
            ]
            if missing:
                raise ValueError(f"{prefix} 缺少已勾选的配套文件：{', '.join(missing[:8])}")
        durations = [_merge_group_duration(segment, content, settings) for _, segment in segments]
        if any(value <= 0 for value in durations):
            raise ValueError(f"{prefix} 存在无法确定时长的片段")
        total = sum(durations)
        outputs = []
        for operation, media_type in enumerate(enabled, start=1):
            if cancelled():
                raise TaskCancelled("任务已取消")
            source_parts = [
                (getattr(segment, media_type), duration)
                for (_, segment), duration in zip(segments, durations)
                if getattr(segment, media_type)
            ]
            if not source_parts:
                report(operation / len(enabled), f"{prefix} 无 {media_type}")
                continue
            sources = [source for source, _ in source_parts]
            media_total = sum(duration for _, duration in source_parts)
            if len(source_parts) != len(segments):
                log(f"{prefix} 的 {media_type} 缺少部分片段；仅合并已有文件")
            suffix = {"audio": ".wav", "video": ".mp4", "textgrid": ".TextGrid"}[media_type]
            output = output_dir / f"{prefix}_merged{suffix}"
            if not _should_write(output, payload["overwrite"], log):
                report(operation / len(enabled), f"跳过 {output.name}")
                continue
            if media_type == "textgrid":
                write_merged_textgrid(source_parts, output)
            else:
                list_file = _concat_file(sources)
                try:
                    run_ffmpeg(
                        settings.ffmpeg,
                        _concat_arguments(list_file, media_type),
                        output,
                        duration=media_total,
                        progress=lambda value, name, op=operation: report(
                            (op - 1 + value) / len(enabled), f"正在合并 {name}"
                        ),
                        log=log,
                        cancelled=cancelled,
                    )
                finally:
                    list_file.unlink(missing_ok=True)
            outputs.append(_result(payload["output_root"], resolver, output))
            report(operation / len(enabled), f"完成 {output.name}")
        return outputs

    files = _parallel_groups(
        list(groups.items()), payload["workers"], process, progress
    )
    return {"summary": f"合并完成，共生成 {len(files)} 个文件", "files": files}


def _format_time(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", "p")


def execute_extract(payload, *, settings, resolver, progress, log, cancelled):
    source_dir = resolver.resolve(payload["input_root"], payload["input_path"], kind="dir")
    output_dir = resolver.resolve(
        payload["output_root"], payload["output_path"], must_exist=False
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    groups = discover_source_sets(source_dir)
    group = groups.get(payload["base_name"].casefold())
    if not group:
        raise ValueError(f"找不到主文件名：{payload['base_name']}")
    content = payload["content"]
    total = _group_duration(group, content, settings)
    ranges = payload["ranges"]
    if total <= 0:
        raise ValueError("无法确定源文件时长")
    if any(item["end"] > total + 1e-4 for item in ranges):
        raise ValueError(f"抽取区间超出源文件时长 {total:.3f}s")

    def process(index, item, report):
        start, end = item["start"], item["end"]
        duration = end - start
        base = f"{group.base}_{_format_time(start)}_{_format_time(end)}"
        outputs = []
        enabled = _enabled(content)
        log(f"抽取 {group.base}：{start:.3f}s–{end:.3f}s")
        for operation, media_type in enumerate(enabled, start=1):
            if cancelled():
                raise TaskCancelled("任务已取消")
            source = getattr(group, media_type)
            if not source:
                log(f"{group.base} 缺少 {media_type}，已跳过该项")
                report(operation / len(enabled), f"缺少 {media_type}")
                continue
            suffix = {"audio": ".wav", "video": ".mp4", "textgrid": ".TextGrid"}[media_type]
            output = output_dir / f"{base}{suffix}"
            if not _should_write(output, payload["overwrite"], log):
                report(operation / len(enabled), f"跳过 {output.name}")
                continue
            if media_type == "video":
                arguments = _video_trim_arguments(source, start, duration)
                run_ffmpeg(
                    settings.ffmpeg, arguments, output, duration=duration,
                    progress=lambda value, name, op=operation: report(
                        (op - 1 + value) / len(enabled), f"正在抽取 {name}"
                    ),
                    log=log, cancelled=cancelled,
                )
            elif media_type == "audio":
                arguments = _audio_trim_arguments(source, start, duration)
                run_ffmpeg(
                    settings.ffmpeg, arguments, output, duration=duration,
                    progress=lambda value, name, op=operation: report(
                        (op - 1 + value) / len(enabled), f"正在抽取 {name}"
                    ),
                    log=log, cancelled=cancelled,
                )
            else:
                write_clipped_textgrid(source, output, start, end)
            outputs.append(_result(payload["output_root"], resolver, output))
            report(operation / len(enabled), f"完成 {output.name}")
        return outputs

    files = _parallel_groups(ranges, payload["workers"], process, progress)
    return {"summary": f"抽取完成，共生成 {len(files)} 个文件", "files": files}
