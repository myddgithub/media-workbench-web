"""Windows entry for local Media Workbench (dev + PyInstaller exe).

Roles:
  (default)  Start web + worker, open browser, block until stopped
  --role=web     Run uvicorn only
  --role=worker  Run media worker only
  --stop         Stop a previously started instance
  --status       Print process / health status
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def install_dir() -> Path:
    """Writable directory next to the exe (or project root in dev)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    """Where bundled package data lives (PyInstaller _MEIPASS or project root)."""
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def runtime_dirs() -> tuple[Path, Path, Path, Path]:
    root = install_dir() / ".local"
    state = root / "state"
    run = root / "run"
    logs = root / "logs"
    for path in (root, state, run, logs):
        path.mkdir(parents=True, exist_ok=True)
    return root, state, run, logs


def parse_env_file(path: Path) -> dict[str, str]:
    config: dict[str, str] = {}
    # utf-8-sig strips a leading BOM (common from Windows editors / Set-Content -Encoding UTF8)
    text = path.read_text(encoding="utf-8-sig")
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SystemExit(f"本地配置行无效：{raw}")
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        if not key:
            raise SystemExit(f"本地配置行无效：{raw}")
        config[key] = value.strip()
    return config


def resolve_path(text: str, base: Path) -> Path:
    expanded = os.path.expandvars(text.strip())
    path = Path(expanded)
    if not path.is_absolute():
        path = (base / path).resolve()
    else:
        path = path.resolve()
    return path


def ensure_local_config() -> dict[str, str]:
    base = install_dir()
    config_path = base / ".env.local"
    example = base / ".env.local.example"
    bundled_example = resource_dir() / ".env.local.example"

    if not config_path.is_file():
        src = example if example.is_file() else bundled_example
        if not src.is_file():
            # Sensible defaults for a fresh exe folder
            ffmpeg_dir = base / "ffmpeg"
            # Use forward slashes in templates so "\f" in "\ffmpeg" is never an escape hazard.
            config_path.write_text(
                "\n".join(
                    [
                        "LOCAL_WEB_HOST=127.0.0.1",
                        "LOCAL_WEB_PORT=8768",
                        "MEDIA_ROOTS=本机D盘=D:/",
                        "FFMPEG_BIN=ffmpeg/ffmpeg.exe",
                        "FFPROBE_BIN=ffmpeg/ffprobe.exe",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            print(f"已创建本地配置：{config_path}")
        else:
            config_path.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"已从模板创建本地配置：{config_path}")
            print("如本机盘符不同，请编辑 MEDIA_ROOTS 后重新启动。")

    config = parse_env_file(config_path)
    required = (
        "LOCAL_WEB_HOST",
        "LOCAL_WEB_PORT",
        "MEDIA_ROOTS",
        "FFMPEG_BIN",
        "FFPROBE_BIN",
    )
    for key in required:
        if not config.get(key):
            raise SystemExit(f"本地配置缺少 {key}：{config_path}")

    config["FFMPEG_BIN"] = str(resolve_path(config["FFMPEG_BIN"], base))
    config["FFPROBE_BIN"] = str(resolve_path(config["FFPROBE_BIN"], base))
    return config


def apply_environment(config: dict[str, str]) -> tuple[str, int]:
    _, state, _, _ = runtime_dirs()
    host = config["LOCAL_WEB_HOST"].strip()
    port = int(config["LOCAL_WEB_PORT"])
    if host not in ("127.0.0.1", "localhost"):
        raise SystemExit(f"本地版只允许监听 127.0.0.1 或 localhost，当前为：{host}")

    os.environ["APP_TITLE"] = "音视频与 TextGrid 处理工作台（本地版）"
    os.environ["MEDIA_ROOTS"] = config["MEDIA_ROOTS"]
    os.environ["STATE_DIR"] = str(state)
    os.environ["DATABASE_PATH"] = str(state / "jobs.sqlite3")
    os.environ["FFMPEG_BIN"] = config["FFMPEG_BIN"]
    os.environ["FFPROBE_BIN"] = config["FFPROBE_BIN"]
    os.environ["JOB_POLL_SECONDS"] = "1"
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    # Project / bundle root for imports in dev; frozen uses PyInstaller path.
    if not is_frozen():
        os.environ["PYTHONPATH"] = str(install_dir())
    return host, port


def assert_binaries(config: dict[str, str]) -> None:
    for key in ("FFMPEG_BIN", "FFPROBE_BIN"):
        path = Path(config[key])
        if not path.is_file():
            raise SystemExit(
                f"{key} 不存在：{path}\n"
                f"请把 ffmpeg.exe / ffprobe.exe 放到 {install_dir() / 'ffmpeg'}，"
                "或修改 .env.local 中的路径。"
            )


def pid_file(role: str) -> Path:
    _, _, run, _ = runtime_dirs()
    return run / f"{role}.pid"


def read_pid(role: str) -> int | None:
    path = pid_file(role)
    if not path.is_file():
        return None
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        path.unlink(missing_ok=True)
        return None
    if not _pid_alive(value):
        path.unlink(missing_ok=True)
        return None
    return value


def write_pid(role: str, pid: int) -> None:
    pid_file(role).write_text(str(pid), encoding="utf-8")


def clear_pid(role: str) -> None:
    pid_file(role).unlink(missing_ok=True)


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        # tasklist is reliable without extra deps
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                text=True,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return str(pid) in out
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass


def self_command(role: str) -> list[str]:
    if is_frozen():
        return [str(Path(sys.executable).resolve()), f"--role={role}"]
    return [sys.executable, str(Path(__file__).resolve()), f"--role={role}"]


def run_web(host: str, port: int) -> None:
    # Env must already be applied before importing app (settings are cached).
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )


def run_worker() -> None:
    from app.worker import main as worker_main

    worker_main()


def wait_healthy(host: str, port: int, timeout: float = 45.0) -> bool:
    url = f"http://{host}:{port}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            if '"status":"ok"' in body.replace(" ", "") or '"status": "ok"' in body:
                if "worker_alive" in body and "true" in body.lower():
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    return False


def cmd_stop() -> int:
    stopped = False
    for role in ("worker", "web", "launcher"):
        pid = read_pid(role)
        if pid is None:
            print(f"{role} 未运行")
            continue
        kill_pid(pid)
        clear_pid(role)
        print(f"已停止 {role}（PID {pid}）")
        stopped = True
    if not stopped:
        print("没有正在运行的本地工作台进程。")
    return 0


def cmd_status() -> int:
    config = ensure_local_config()
    host = config["LOCAL_WEB_HOST"]
    port = int(config["LOCAL_WEB_PORT"])
    for role in ("launcher", "web", "worker"):
        pid = read_pid(role)
        print(f"{role} PID：{pid if pid is not None else '未运行'}")
    print(f"本地地址：http://{host}:{port}")
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=3) as resp:
            print(f"健康状态：{resp.read().decode('utf-8', errors='replace')}")
        return 0
    except Exception as exc:
        print(f"健康状态：不可访问（{exc}）")
        return 1


def cmd_start(no_browser: bool) -> int:
    config = ensure_local_config()
    assert_binaries(config)
    host, port = apply_environment(config)
    _, _, _, logs = runtime_dirs()

    if read_pid("web") or read_pid("worker"):
        print("检测到已有实例，先尝试打开页面…")
        if wait_healthy(host, port, timeout=5):
            if not no_browser:
                webbrowser.open(f"http://{host}:{port}")
            print(f"本地工作台已在运行：http://{host}:{port}")
            return 0
        print("旧实例不健康，正在清理后重启…")
        cmd_stop()

    write_pid("launcher", os.getpid())

    creation = 0
    if os.name == "nt":
        # Detach child consoles less noisily; still inherit env.
        creation = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    web_out = open(logs / "web.out.log", "a", encoding="utf-8")
    web_err = open(logs / "web.err.log", "a", encoding="utf-8")
    worker_out = open(logs / "worker.out.log", "a", encoding="utf-8")
    worker_err = open(logs / "worker.err.log", "a", encoding="utf-8")

    web = subprocess.Popen(
        self_command("web"),
        cwd=str(install_dir()),
        env=os.environ.copy(),
        stdout=web_out,
        stderr=web_err,
        creationflags=creation,
    )
    write_pid("web", web.pid)

    worker = subprocess.Popen(
        self_command("worker"),
        cwd=str(install_dir()),
        env=os.environ.copy(),
        stdout=worker_out,
        stderr=worker_err,
        creationflags=creation,
    )
    write_pid("worker", worker.pid)

    try:
        if not wait_healthy(host, port, timeout=60):
            raise SystemExit(
                f"Web/Worker 未在 60 秒内进入健康状态，请查看日志目录：{logs}"
            )
        print(f"本地工作台已启动：http://{host}:{port}")
        print(f"Web PID：{web.pid}；Worker PID：{worker.pid}")
        print(f"允许访问：{config['MEDIA_ROOTS']}")
        print(f"状态目录：{install_dir() / '.local' / 'state'}")
        print("关闭本窗口将停止服务。也可运行：MediaWorkbenchWeb.exe --stop")
        if not no_browser:
            webbrowser.open(f"http://{host}:{port}")

        # Keep parent alive; stop children when it exits.
        while True:
            if web.poll() is not None:
                raise SystemExit(f"Web 进程已退出，代码 {web.returncode}。详见 {logs}")
            if worker.poll() is not None:
                raise SystemExit(
                    f"Worker 进程已退出，代码 {worker.returncode}。详见 {logs}"
                )
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止…")
        return 0
    finally:
        for proc, role in ((worker, "worker"), (web, "web")):
            if proc.poll() is None:
                kill_pid(proc.pid)
            clear_pid(role)
        clear_pid("launcher")
        for fh in (web_out, web_err, worker_out, worker_err):
            try:
                fh.close()
            except Exception:
                pass
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="音视频与 TextGrid 处理工作台（本地版）")
    parser.add_argument(
        "--role",
        choices=("launcher", "web", "worker"),
        default="launcher",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--stop", action="store_true", help="停止本地 Web/Worker")
    parser.add_argument("--status", action="store_true", help="查看运行状态")
    parser.add_argument("--no-browser", action="store_true", help="启动时不打开浏览器")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.stop:
        return cmd_stop()
    if args.status:
        return cmd_status()

    if args.role == "web":
        config = ensure_local_config()
        assert_binaries(config)
        host, port = apply_environment(config)
        run_web(host, port)
        return 0
    if args.role == "worker":
        config = ensure_local_config()
        assert_binaries(config)
        apply_environment(config)
        run_worker()
        return 0

    return cmd_start(no_browser=args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
