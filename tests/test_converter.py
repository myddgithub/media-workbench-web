from pathlib import Path

from app.converter import (
    build_conversion_arguments,
    matches_mode,
    output_extension,
    scan_conversion_files,
)


def base_payload(**updates):
    payload = {
        "mode": "video_to_audio", "audio_codec": "pcm_s16le",
        "audio_bitrate": "192k", "sample_rate": 16000, "channels": 1,
        "video_codec": "libx264", "crf": 23, "resolution": "",
        "preset": "medium", "video_format": ".mp4",
    }
    payload.update(updates)
    return payload


def test_video_to_corpus_wav_arguments():
    args = build_conversion_arguments(Path("show.mp4"), base_payload())
    assert args[:4] == ["-hide_banner", "-y", "-i", "show.mp4"]
    assert "-vn" in args
    assert args[args.index("-ar") + 1] == "16000"
    assert args[args.index("-ac") + 1] == "1"
    assert output_extension(base_payload()) == ".wav"


def test_qsv_video_arguments():
    payload = base_payload(mode="video_to_video", video_codec="h264_qsv", resolution="1280x720")
    args = build_conversion_arguments(Path("in.mkv"), payload)
    assert args[args.index("-c:v") + 1] == "h264_qsv"
    assert "scale=1280:720" in args
    assert "-global_quality" in args
    assert "-preset" not in args


def test_scan_conversion_files_respects_mode_and_recursion(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"")
    (tmp_path / "b.wav").write_bytes(b"")
    child = tmp_path / "child"
    child.mkdir()
    (child / "c.mkv").write_bytes(b"")
    assert len(scan_conversion_files(tmp_path, "video_to_audio", recursive=True)) == 2
    assert len(scan_conversion_files(tmp_path, "video_to_audio", recursive=False)) == 1
    assert matches_mode(Path("VOICE.FLAC"), "audio_to_audio")
