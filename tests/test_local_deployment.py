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


def test_local_one_click_commands_are_present():
    for name in ("start-local.cmd", "stop-local.cmd", "status-local.cmd"):
        assert (ROOT / name).is_file()
