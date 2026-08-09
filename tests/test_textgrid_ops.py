import pytest
from textgrid import IntervalTier, PointTier, TextGrid

from app.textgrid_ops import calculate_segments, clipped_textgrid, merged_textgrid, semantic_intervals


def make_grid(duration=10.0):
    grid = TextGrid(minTime=0, maxTime=duration)
    words = IntervalTier(name="words", minTime=0, maxTime=duration)
    words.add(0, 4, "甲")
    words.add(4, duration, "乙")
    points = PointTier(name="events", minTime=0, maxTime=duration)
    points.add(2, "P1")
    points.add(8, "P2")
    grid.append(words)
    grid.append(points)
    return grid


def test_nearest_sg_boundary_prefers_closest():
    segments = calculate_segments(20, 7, [(0, 5), (5, 12), (12, 20)])
    assert segments[0] == (0, 5)
    assert segments[1] == (5, 12)
    assert segments[-1][1] == pytest.approx(20 - 1e-5)


def test_semantic_tier_names_are_case_insensitive():
    grid = TextGrid(minTime=0, maxTime=10)
    sg = IntervalTier(name="SG", minTime=0, maxTime=10)
    sg.add(0, 5, "句一")
    sg.add(5, 10, "")
    grid.append(sg)
    assert semantic_intervals(grid) == [(0.0, 5.0)]


def test_clip_preserves_interval_and_point_offsets():
    clipped = clipped_textgrid(make_grid(), 2, 7)
    assert clipped.maxTime == 5
    words = clipped.getFirst("words")
    assert [(item.minTime, item.maxTime, item.mark) for item in words] == [
        (0.0, 2.0, "甲"), (2.0, 5.0, "乙")
    ]
    events = clipped.getFirst("events")
    assert [(point.time, point.mark) for point in events] == [(0.0, "P1")]


def test_merge_uses_supplied_durations_for_offsets():
    first = clipped_textgrid(make_grid(), 0, 4)
    second = clipped_textgrid(make_grid(), 4, 7)
    merged = merged_textgrid([(first, 4), (second, 3)])
    assert merged.maxTime == 7
    intervals = merged.getFirst("words")
    assert intervals[-1].maxTime == 7
