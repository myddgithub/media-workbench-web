from app.cme import SourceSet, _merge_group_duration, discover_source_sets, scan_cme
from app.config import Settings
from textgrid import IntervalTier, TextGrid


def test_discover_triplets_case_insensitively(tmp_path):
    for name in ("demo.mp4", "demo.wav", "demo.TextGrid", "other.WAV"):
        (tmp_path / name).write_bytes(b"")
    groups = discover_source_sets(tmp_path)
    assert groups["demo"].audio.name == "demo.wav"
    assert groups["demo"].video.name == "demo.mp4"
    assert groups["demo"].textgrid.name == "demo.TextGrid"
    assert groups["other"].audio.name == "other.WAV"


def test_scan_detects_merge_prefixes(tmp_path):
    for name in ("show.mp4", "show.wav", "show.TextGrid", "show_seg000.wav", "show_seg001.wav"):
        (tmp_path / name).write_bytes(b"")
    result = scan_cme(tmp_path)
    assert result["groups"] == 1
    assert result["segments"] == 2
    assert result["prefixes"] == ["show"]


def test_merge_duration_prefers_textgrid_over_media(monkeypatch, tmp_path):
    tg_path = tmp_path / "part.TextGrid"
    grid = TextGrid(minTime=0, maxTime=3.25)
    tier = IntervalTier(name="words", minTime=0, maxTime=3.25)
    tier.add(0, 3.25, "内容")
    grid.append(tier)
    grid.write(str(tg_path))
    video = tmp_path / "part.mp4"
    video.write_bytes(b"")
    settings = Settings({}, tmp_path, tmp_path / "db", "ffmpeg", "ffprobe", 1, "test")
    monkeypatch.setattr("app.cme.probe_duration", lambda *_: 9.0)
    duration = _merge_group_duration(
        SourceSet("part", video=video, textgrid=tg_path),
        {"textgrid": True, "video": True, "audio": False},
        settings,
    )
    assert duration == 3.25
