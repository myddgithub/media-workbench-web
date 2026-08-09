from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from textgrid import IntervalTier, PointTier, TextGrid

from .media import atomic_write_textgrid


SG_TIER_NAMES = {"sg", "sentence", "段落", "sentence group", "语段"}


def read_textgrid(path: Path) -> TextGrid:
    return TextGrid.fromFile(str(path))


def _tier_points(tier):
    return getattr(tier, "points", list(tier))


def semantic_intervals(textgrid: TextGrid) -> list[tuple[float, float]]:
    for tier in textgrid:
        if tier.name.strip().casefold() in SG_TIER_NAMES and isinstance(tier, IntervalTier):
            return [
                (float(interval.minTime), float(interval.maxTime))
                for interval in tier.intervals
                if str(interval.mark).strip()
            ]
    return []


def calculate_segments(
    total: float,
    step: float,
    sg_intervals: list[tuple[float, float]] | None = None,
) -> list[tuple[float, float]]:
    """Port of CME-GUI v4's nearest-SG-boundary algorithm."""
    points: list[tuple[float, float]] = []
    start = 0.0
    semantic = sg_intervals or []
    while start < total:
        if semantic:
            ideal_end = start + step
            if ideal_end >= total:
                end = total - 1e-6
            else:
                previous = [end for begin, end in semantic if start < end <= ideal_end]
                following = [begin for begin, end in semantic if ideal_end <= begin < total]
                candidates = []
                if previous:
                    candidate = max(previous)
                    candidates.append((abs(candidate - ideal_end), candidate))
                if following:
                    candidate = min(following)
                    candidates.append((abs(candidate - ideal_end), candidate))
                end = min(candidates)[1] if candidates else ideal_end
        else:
            end = min(start + step, total)
        if total - end < 1e-5:
            end = total - 1e-5
        duration = end - start
        if duration < 0.5:
            break
        points.append((start, end))
        start = end
    return points


def clipped_textgrid(source: TextGrid, start: float, end: float) -> TextGrid:
    duration = end - start
    output = TextGrid(minTime=0, maxTime=duration)
    for tier in source:
        if isinstance(tier, IntervalTier):
            new_tier = IntervalTier(name=tier.name, minTime=0, maxTime=duration)
            for interval in tier.intervals:
                if interval.maxTime <= start - 1e-6 or interval.minTime >= end + 1e-6:
                    continue
                new_min = max(float(interval.minTime) - start, 0)
                new_max = min(float(interval.maxTime) - start, duration)
                if new_max > new_min + 1e-6:
                    new_tier.add(new_min, new_max, interval.mark)
        elif isinstance(tier, PointTier):
            new_tier = PointTier(name=tier.name, minTime=0, maxTime=duration)
            for point in _tier_points(tier):
                value = float(point.time) - start
                if -1e-6 <= value <= duration + 1e-6:
                    new_tier.add(min(max(value, 0), duration), point.mark)
        else:
            continue
        output.append(new_tier)
    output.maxTime = duration
    return output


def write_clipped_textgrid(source_path: Path, output_path: Path, start: float, end: float) -> None:
    atomic_write_textgrid(clipped_textgrid(read_textgrid(source_path), start, end), output_path)


def merged_textgrid(parts: list[tuple[TextGrid, float]]) -> TextGrid:
    total = sum(duration for _, duration in parts)
    output = TextGrid(minTime=0, maxTime=total)
    tiers: OrderedDict[str, IntervalTier | PointTier] = OrderedDict()
    for grid, _ in parts:
        for tier in grid:
            if tier.name not in tiers:
                if isinstance(tier, IntervalTier):
                    tiers[tier.name] = IntervalTier(name=tier.name, minTime=0, maxTime=total)
                elif isinstance(tier, PointTier):
                    tiers[tier.name] = PointTier(name=tier.name, minTime=0, maxTime=total)
    for tier in tiers.values():
        output.append(tier)

    offset = 0.0
    for grid, duration in parts:
        for source_tier in grid:
            target = tiers.get(source_tier.name)
            if isinstance(source_tier, IntervalTier) and isinstance(target, IntervalTier):
                for interval in source_tier.intervals:
                    target.add(
                        float(interval.minTime) + offset,
                        float(interval.maxTime) + offset,
                        interval.mark,
                    )
            elif isinstance(source_tier, PointTier) and isinstance(target, PointTier):
                for point in _tier_points(source_tier):
                    target.add(float(point.time) + offset, point.mark)
        offset += duration
    output.maxTime = total
    return output


def write_merged_textgrid(parts: list[tuple[Path, float]], output_path: Path) -> None:
    grids = [(read_textgrid(path), duration) for path, duration in parts]
    atomic_write_textgrid(merged_textgrid(grids), output_path)
