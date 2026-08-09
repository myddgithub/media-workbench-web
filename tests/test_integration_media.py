import shutil
import subprocess

import pytest

from app.config import MediaRoot, Settings
from app.converter import execute_conversion
from app.paths import PathResolver


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg unavailable")
def test_real_audio_conversion(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    wav = source / "tone.wav"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4",
        "-c:a", "pcm_s16le", str(wav),
    ], check=True)
    roots = {
        "source": MediaRoot("source", "Source", source),
        "output": MediaRoot("output", "Output", output),
    }
    settings = Settings(
        roots=roots, state_dir=tmp_path, database_path=tmp_path / "db.sqlite3",
        ffmpeg="ffmpeg", ffprobe="ffprobe", poll_seconds=1, app_title="Test",
    )
    payload = {
        "input_root": "source", "input_path": "tone.wav",
        "output_root": "output", "output_path": "converted",
        "workers": 1, "overwrite": False, "mode": "audio_to_audio", "recursive": True,
        "audio_codec": "libmp3lame", "audio_bitrate": "128k", "sample_rate": 16000,
        "channels": 1, "video_codec": "libx264", "crf": 23, "resolution": "",
        "preset": "medium", "video_format": ".mp4",
    }
    result = execute_conversion(
        payload, settings=settings, resolver=PathResolver(roots),
        progress=lambda *_: None, log=lambda *_: None, cancelled=lambda: False,
    )
    assert result["summary"].startswith("转换完成 1")
    assert (output / "converted" / "tone.mp3").stat().st_size > 0
