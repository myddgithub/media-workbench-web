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
    # Bilingual end-user readme in the zip
    assert "【English】" in pack
    assert "Media & TextGrid Workbench" in pack
    assert "中文 / EN" in pack
    # Embeddable ._pth ignores PYTHONPATH; project root must be listed explicitly.
    assert '"..\\\\.."' in pack or r'"..\.."' in pack


def test_exe_launcher_and_pack_scripts_exist():
    assert (ROOT / "launcher.py").is_file()
    assert (ROOT / "MediaWorkbenchWeb.spec").is_file()
    assert (ROOT / "scripts" / "pack_local_exe.ps1").is_file()
    assert (ROOT / "scripts" / "pack_local_exe.sh").is_file()
    launcher = (ROOT / "launcher.py").read_text(encoding="utf-8")
    assert "def cmd_start" in launcher
    assert "127.0.0.1" in launcher
    assert "--stop" in launcher
    assert 'DEPLOYMENT"] = "local"' in launcher or 'DEPLOYMENT"]="local"' in launcher
    assert "def bi(" in launcher
    pack_exe = (ROOT / "scripts" / "pack_local_exe.ps1").read_text(encoding="utf-8")
    assert "【English】" in pack_exe
    assert "中文 / EN" in pack_exe


def test_ui_i18n_static_assets_present():
    static = ROOT / "app" / "static"
    assert (static / "i18n.js").is_file()
    i18n = (static / "i18n.js").read_text(encoding="utf-8")
    assert "appTitleLocal" in i18n
    assert "setDeployment" in i18n
    assert "Media & TextGrid Workbench" in i18n
    html = (static / "index.html").read_text(encoding="utf-8")
    assert "i18n.js" in html or "data-i18n" in html
    assert 'data-i18n="appTitle"' in html
    common = (ROOT / "scripts" / "local_common.ps1").read_text(encoding="utf-8")
    assert 'DEPLOYMENT = "local"' in common

