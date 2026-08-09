from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_deployment_is_loopback_only_and_has_separate_state():
    start = (ROOT / "scripts" / "start_local.ps1").read_text(encoding="utf-8")
    common = (ROOT / "scripts" / "local_common.ps1").read_text(encoding="utf-8")
    example = (ROOT / ".env.local.example").read_text(encoding="utf-8")

    assert 'if ($webHost -ne "127.0.0.1"' in start
    assert 'if ($listener -and $null -eq $webProcessId)' in start
    assert 'Join-Path $ProjectRoot ".local"' in common
    assert "MEDIA_ROOTS=本机D盘=D:\\" in example
    assert "192.168.1.2" not in example
    assert "function Resolve-LocalPath" in common
    assert "Ensure-LocalPythonEnvironment" in common
    assert "vendor\\python\\python.exe" in common
    assert 'PythonRuntimeKind = "portable"' in common


def test_local_one_click_commands_are_present():
    for name in ("start-local.cmd", "stop-local.cmd", "status-local.cmd"):
        assert (ROOT / name).is_file()
    assert (ROOT / "scripts" / "setup_local.ps1").is_file()
    assert (ROOT / "scripts" / "pack_local_dist.sh").is_file()


def test_local_powershell_scripts_are_utf8_bom_for_windows_powershell_51():
    for name in (
        "local_common.ps1",
        "start_local.ps1",
        "stop_local.ps1",
        "status_local.ps1",
        "setup_local.ps1",
    ):
        assert (ROOT / "scripts" / name).read_bytes().startswith(b"\xef\xbb\xbf")


def test_pack_local_dist_script_is_zero_dep_standalone():
    pack = (ROOT / "scripts" / "pack_local_dist.sh").read_text(encoding="utf-8")
    assert "vendor/ffmpeg" in pack
    assert "vendor/python" in pack
    assert "embed-amd64" in pack
    assert "standalone" in pack
    assert "使用说明.txt" in pack
    assert "不需要安装 Python" in pack
    assert "FFMPEG_BIN=vendor\\ffmpeg\\ffmpeg.exe" in pack
    # Embeddable ._pth ignores PYTHONPATH; project root must be listed explicitly.
    assert '"..\\\\.."' in pack or r'"..\.."' in pack