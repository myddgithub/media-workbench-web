#!/usr/bin/env bash
# Build a zero-dependency Windows local distribution zip for media-workbench-web.
# Bundles: app + scripts + portable CPython + site-packages + ffmpeg.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_ROOT="${ROOT}/dist"
CACHE_DIR="${DIST_ROOT}/.cache"
STAGING="${DIST_ROOT}/media-workbench-web-local"
VERSION="$(python3 - <<'PY' "${ROOT}/app/__init__.py"
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
print(m.group(1) if m else "0.0.0")
PY
)"
STAMP="$(date +%Y%m%d)"
ZIP_NAME="media-workbench-web-local-v${VERSION}-${STAMP}-standalone.zip"
ZIP_PATH="${DIST_ROOT}/${ZIP_NAME}"

# Prefer MediaConverter bundled ffmpeg; allow override.
FFMPEG_SRC="${FFMPEG_SRC:-/mnt/d/mypy/MediaConverter/ffmpeg}"
if [[ ! -f "${FFMPEG_SRC}/ffmpeg.exe" || ! -f "${FFMPEG_SRC}/ffprobe.exe" ]]; then
  echo "ERROR: Windows ffmpeg/ffprobe not found under: ${FFMPEG_SRC}" >&2
  echo "Set FFMPEG_SRC to a directory containing ffmpeg.exe and ffprobe.exe." >&2
  exit 1
fi

# Portable CPython embeddable (Windows amd64)
PYTHON_VERSION="${PYTHON_VERSION:-3.12.8}"
PYTHON_EMBED_URL="${PYTHON_EMBED_URL:-https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip}"
PYTHON_EMBED_ZIP="${CACHE_DIR}/python-${PYTHON_VERSION}-embed-amd64.zip"

# Host Windows Python used only at pack time to install wheels into the embeddable runtime.
HOST_WIN_PYTHON="${HOST_WIN_PYTHON:-}"
if [[ -z "${HOST_WIN_PYTHON}" ]]; then
  if command -v powershell.exe >/dev/null 2>&1; then
    HOST_WIN_PYTHON="$(
      powershell.exe -NoProfile -Command "
        \$py = Get-Command py.exe -ErrorAction SilentlyContinue
        if (\$py) {
          try {
            \$p = & \$py.Source -3.12 -c 'import sys; print(sys.executable)' 2>\$null
            if (\$LASTEXITCODE -eq 0 -and \$p) { \$p.Trim(); exit 0 }
          } catch {}
          try {
            \$p = & \$py.Source -3 -c 'import sys; print(sys.executable)' 2>\$null
            if (\$LASTEXITCODE -eq 0 -and \$p) { \$p.Trim(); exit 0 }
          } catch {}
        }
        \$python = Get-Command python.exe -ErrorAction SilentlyContinue
        if (\$python) { \$python.Source; exit 0 }
        exit 1
      " 2>/dev/null | tr -d '\r' | tail -n 1
    )" || true
  fi
fi
if [[ -z "${HOST_WIN_PYTHON}" ]]; then
  echo "ERROR: Need Windows Python at pack time to install dependencies into the portable runtime." >&2
  echo "Install Python 3.12 on Windows, or set HOST_WIN_PYTHON='C:\\Path\\to\\python.exe'." >&2
  exit 1
fi

to_win_path() {
  if command -v wslpath >/dev/null 2>&1; then
    wslpath -w "$1"
  else
    # Git Bash / MSYS style
    cygpath -w "$1" 2>/dev/null || echo "$1"
  fi
}

echo "==> Portable Python ${PYTHON_VERSION} (embeddable)"
mkdir -p "${CACHE_DIR}"
if [[ ! -f "${PYTHON_EMBED_ZIP}" ]]; then
  echo "    downloading ${PYTHON_EMBED_URL}"
  curl -fL --retry 3 -o "${PYTHON_EMBED_ZIP}.partial" "${PYTHON_EMBED_URL}"
  mv "${PYTHON_EMBED_ZIP}.partial" "${PYTHON_EMBED_ZIP}"
fi

echo "==> Staging ${STAGING}"
rm -rf "${STAGING}"
mkdir -p "${STAGING}/app/static" "${STAGING}/scripts" \
  "${STAGING}/vendor/ffmpeg" "${STAGING}/vendor/python" "${DIST_ROOT}"

# Application code (no bytecode)
rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' \
  "${ROOT}/app/" "${STAGING}/app/"

# Local Windows scripts + launcher cmd files (setup_local optional for non-portable dev only)
for f in local_common.ps1 start_local.ps1 stop_local.ps1 status_local.ps1 setup_local.ps1; do
  cp -a "${ROOT}/scripts/${f}" "${STAGING}/scripts/${f}"
done
cp -a "${ROOT}/start-local.cmd" "${ROOT}/stop-local.cmd" "${ROOT}/status-local.cmd" "${STAGING}/"
cp -a "${ROOT}/requirements.txt" "${STAGING}/"
cp -a "${ROOT}/README.md" "${STAGING}/README.md"

# Portable local config
cat > "${STAGING}/.env.local.example" <<'EOF'
# 本地版只监听当前电脑，不向局域网开放。
LOCAL_WEB_HOST=127.0.0.1
LOCAL_WEB_PORT=8768

# 只开放真正的本地数据盘；按对方电脑实际情况修改盘符/目录。
# 可用环境变量，例如：用户文档=%USERPROFILE%\Documents
MEDIA_ROOTS=本机D盘=D:\

# 分发包自带的 FFmpeg（相对本目录，也可写成绝对路径）
FFMPEG_BIN=vendor\ffmpeg\ffmpeg.exe
FFPROBE_BIN=vendor\ffmpeg\ffprobe.exe
EOF

# Bundled Windows FFmpeg
cp -a "${FFMPEG_SRC}/ffmpeg.exe" "${STAGING}/vendor/ffmpeg/ffmpeg.exe"
cp -a "${FFMPEG_SRC}/ffprobe.exe" "${STAGING}/vendor/ffmpeg/ffprobe.exe"

# Extract embeddable CPython
echo "==> Extracting embeddable CPython"
python3 - <<'PY' "${PYTHON_EMBED_ZIP}" "${STAGING}/vendor/python"
import pathlib, sys, zipfile
src, dest = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
dest.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(src) as zf:
    zf.extractall(dest)
print("extracted", len(list(dest.iterdir())), "top-level entries")
PY

# Enable site-packages for embeddable runtime
PTH_FILE="$(ls "${STAGING}/vendor/python"/python*._pth | head -n 1)"
if [[ -z "${PTH_FILE}" || ! -f "${PTH_FILE}" ]]; then
  echo "ERROR: python*._pth not found in embeddable package" >&2
  exit 1
fi
# Embeddable ._pth IGNORES PYTHONPATH and process cwd. List every needed root here.
# vendor/python -> ../.. is the distribution project root (so `import app` works).
python3 - <<'PY' "${PTH_FILE}"
from pathlib import Path
import sys
pth = Path(sys.argv[1])
# Keep a minimal deterministic path list.
content = "\n".join(
    [
        "python312.zip",
        ".",
        "Lib\\site-packages",
        "..\\..",  # project root: media-workbench-web-local/
        "import site",
    ]
) + "\n"
# Use actual zip name from original pth if not python312.zip
for raw in pth.read_text(encoding="utf-8").splitlines():
    s = raw.strip()
    if s.endswith(".zip") and not s.startswith("#"):
        content = content.replace("python312.zip", s, 1)
        break
pth.write_text(content, encoding="utf-8")
print(pth.name, "=>")
print(pth.read_text(encoding="utf-8"))
PY
SITE_PACKAGES="${STAGING}/vendor/python/Lib/site-packages"
mkdir -p "${SITE_PACKAGES}"

echo "==> Installing Windows wheels into portable runtime"
echo "    host python: ${HOST_WIN_PYTHON}"
WIN_REQ="$(to_win_path "${STAGING}/requirements.txt")"
WIN_TARGET="$(to_win_path "${SITE_PACKAGES}")"
# Use host Windows Python so we get win_amd64 wheels; install into embeddable site-packages.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \
  "& '${HOST_WIN_PYTHON}' -m pip install --upgrade pip; \
   if (\$LASTEXITCODE -ne 0) { exit \$LASTEXITCODE }; \
   & '${HOST_WIN_PYTHON}' -m pip install \
     --target '${WIN_TARGET}' \
     --upgrade \
     --disable-pip-version-check \
     -r '${WIN_REQ}'; \
   exit \$LASTEXITCODE"

echo "==> Verifying portable imports (Windows)"
WIN_PY="$(to_win_path "${STAGING}/vendor/python/python.exe")"
WIN_PY_HOME="$(to_win_path "${STAGING}/vendor/python")"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \
  "\$env:PYTHONHOME = '${WIN_PY_HOME}'; \
   \$env:PYTHONNOUSERSITE = '1'; \
   Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue; \
   & '${WIN_PY}' -c \"import fastapi, uvicorn, pydantic, textgrid; print('imports-ok', fastapi.__version__)\"; \
   if (\$LASTEXITCODE -ne 0) { exit \$LASTEXITCODE }; \
   & '${WIN_PY}' -c \"import uvicorn; print('uvicorn-ok')\"; \
   exit \$LASTEXITCODE"

# Marker so users know this is a standalone build
cat > "${STAGING}/vendor/python/PORTABLE_RUNTIME.txt" <<EOF
media-workbench-web portable CPython ${PYTHON_VERSION} embed-amd64
built=$(date -Iseconds)
host_pack_python=${HOST_WIN_PYTHON}
EOF

# End-user bilingual readme (zh + en)
cat > "${STAGING}/使用说明.txt" <<'EOF'
音视频与 TextGrid 处理工作台 — Windows 本地版（零依赖分发包）
Media & TextGrid Workbench — Windows local edition (zero-dep package)
====================================================================

【中文】
一、对方电脑需要准备什么
------------------------
1. Windows 10/11（64 位）
2. 不需要安装 Python
3. 不需要安装 FFmpeg
4. 不需要联网（首次启动也不需要装依赖）

本压缩包已内置：
- 便携 Python 运行时（vendor\python）
- 全部 Python 依赖
- ffmpeg / ffprobe（vendor\ffmpeg）

二、怎么用
----------
1. 解压到任意路径（建议路径不要过长；需要对该目录有写权限，用于 .local 任务库）
2. 用记事本打开 .env.local.example，确认 MEDIA_ROOTS 指向对方本机数据盘
   - 默认是：本机D盘=D:\
   - 若没有 D 盘，可改成例如：本机C盘=C:\Users\用户名\Videos
3. 双击 start-local.cmd
   - 成功后浏览器打开 http://127.0.0.1:8768
4. 页面右上角可切换 中文 / EN
5. 查看状态：双击 status-local.cmd
6. 停止服务：双击 stop-local.cmd

三、注意
--------
- 只监听本机 127.0.0.1，局域网其他电脑无法访问（有意设计）
- 任务库与日志在解压目录下的 .local\，不会影响 NAS 上的部署
- 不要删除 vendor\python 或 vendor\ffmpeg
- 不要把 NAS 网络映射盘写进 MEDIA_ROOTS，除非明确要在本机处理 NAS 文件
- 杀毒软件若拦截 python.exe / ffmpeg.exe，请添加信任

四、常见问题
------------
Q: 提示便携 Python 运行时损坏？
A: 重新解压完整 zip，勿只拷贝部分文件；勿用“在线解压”直接运行。

Q: 提示 MEDIA_ROOTS 路径不存在 / 无法扫描？
A: 编辑项目根目录的 .env.local（首次启动后由模板生成），改成真实存在的本地目录

Q: 端口被占用？
A: 修改 .env.local 里的 LOCAL_WEB_PORT，或先 stop-local.cmd 再启动

Q: 强制停止？
A: powershell -ExecutionPolicy Bypass -File scripts\stop_local.ps1 -Force

【English】
Requirements: Windows 10/11 x64. No Python / FFmpeg / network install needed.
Bundled: portable Python (vendor\python), deps, ffmpeg/ffprobe (vendor\ffmpeg).

How to use
----------
1. Unzip to a writable folder (job DB lives under .local\)
2. Check MEDIA_ROOTS in .env.local.example (default: 本机D盘=D:\)
3. Double-click start-local.cmd → http://127.0.0.1:8768
4. Top-right: switch 中文 / EN
5. status-local.cmd / stop-local.cmd for status and stop

Notes: loopback only (127.0.0.1); do not delete vendor\; do not point MEDIA_ROOTS
at NAS mapped drives unless intentional. Antivirus may need an allow-list.
EOF

# Exclude runtime artifacts if any leaked
find "${STAGING}" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "${STAGING}" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
rm -rf "${STAGING}/.venv" "${STAGING}/.local" "${STAGING}/.env.local" 2>/dev/null || true
# Drop pip metadata caches that bloat the zip slightly (keep dist-info)
rm -rf "${SITE_PACKAGES}/pip" "${SITE_PACKAGES}/pip-*" \
  "${SITE_PACKAGES}/setuptools" "${SITE_PACKAGES}/setuptools-*" \
  "${SITE_PACKAGES}/wheel" "${SITE_PACKAGES}/wheel-*" \
  "${SITE_PACKAGES}/pkg_resources" 2>/dev/null || true
find "${SITE_PACKAGES}" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

echo "==> Creating ${ZIP_PATH}"
rm -f "${ZIP_PATH}"
python3 - <<'PY' "${STAGING}" "${ZIP_PATH}"
import pathlib, sys, zipfile
staging = pathlib.Path(sys.argv[1])
zip_path = pathlib.Path(sys.argv[2])
base = staging.name
count = 0
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for path in sorted(staging.rglob("*")):
        if path.is_file():
            arc = f"{base}/{path.relative_to(staging).as_posix()}"
            zf.write(path, arcname=arc)
            count += 1
print(zip_path)
print("files:", count)
PY

cat > "${DIST_ROOT}/LATEST_LOCAL_DIST.txt" <<EOF
${ZIP_NAME}
version=${VERSION}
kind=standalone-zero-dep
python=${PYTHON_VERSION}-embed-amd64
built=$(date -Iseconds)
ffmpeg_src=${FFMPEG_SRC}
host_pack_python=${HOST_WIN_PYTHON}
EOF

ls -lh "${ZIP_PATH}"
echo "DONE: ${ZIP_PATH}"
