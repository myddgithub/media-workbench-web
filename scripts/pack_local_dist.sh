#!/usr/bin/env bash
# Build a Windows-ready local distribution zip for media-workbench-web.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_ROOT="${ROOT}/dist"
STAGING="${DIST_ROOT}/media-workbench-web-local"
VERSION="$(python3 - <<'PY' "${ROOT}/app/__init__.py"
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
print(m.group(1) if m else "0.0.0")
PY
)"
STAMP="$(date +%Y%m%d)"
ZIP_NAME="media-workbench-web-local-v${VERSION}-${STAMP}.zip"
ZIP_PATH="${DIST_ROOT}/${ZIP_NAME}"

# Prefer MediaConverter bundled ffmpeg; allow override.
FFMPEG_SRC="${FFMPEG_SRC:-/mnt/d/mypy/MediaConverter/ffmpeg}"
if [[ ! -f "${FFMPEG_SRC}/ffmpeg.exe" || ! -f "${FFMPEG_SRC}/ffprobe.exe" ]]; then
  echo "ERROR: Windows ffmpeg/ffprobe not found under: ${FFMPEG_SRC}" >&2
  echo "Set FFMPEG_SRC to a directory containing ffmpeg.exe and ffprobe.exe." >&2
  exit 1
fi

echo "==> Staging ${STAGING}"
rm -rf "${STAGING}"
mkdir -p "${STAGING}/app/static" "${STAGING}/scripts" "${STAGING}/vendor/ffmpeg" "${DIST_ROOT}"

# Application code (no bytecode)
rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' \
  "${ROOT}/app/" "${STAGING}/app/"

# Local Windows scripts + launcher cmd files
for f in local_common.ps1 start_local.ps1 stop_local.ps1 status_local.ps1 setup_local.ps1; do
  cp -a "${ROOT}/scripts/${f}" "${STAGING}/scripts/${f}"
done
cp -a "${ROOT}/start-local.cmd" "${ROOT}/stop-local.cmd" "${ROOT}/status-local.cmd" "${STAGING}/"

cp -a "${ROOT}/requirements.txt" "${STAGING}/"
cp -a "${ROOT}/README.md" "${STAGING}/README.md"

# Portable local config: relative ffmpeg + default D: root (user can edit)
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

# End-user Chinese readme for the zip
cat > "${STAGING}/使用说明.txt" <<'EOF'
音视频与 TextGrid 处理工作台 — Windows 本地版（分发包）
========================================================

一、对方电脑需要准备什么
------------------------
1. Windows 10/11（64 位）
2. 已安装 Python 3.10、3.11 或 3.12（推荐 3.11）
   - 官网：https://www.python.org/downloads/windows/
   - 安装时勾选 “Add python.exe to PATH”
3. 本压缩包已内置 ffmpeg / ffprobe，一般不必再装 FFmpeg

二、怎么用
----------
1. 解压到任意英文或中文路径（建议路径不要太深、不要只有只读权限）
2. 用记事本打开 .env.local.example，确认 MEDIA_ROOTS 指向对方本机数据盘
   - 默认是：本机D盘=D:\
   - 若没有 D 盘，可改成例如：本机C盘=C:\Users\用户名\Videos
3. 双击 start-local.cmd
   - 首次启动会自动创建 .venv 并安装依赖（需联网几分钟）
   - 成功后浏览器打开 http://127.0.0.1:8768
4. 查看状态：双击 status-local.cmd
5. 停止服务：双击 stop-local.cmd

三、注意
--------
- 只监听本机 127.0.0.1，局域网其他电脑无法访问（有意设计）
- 任务库与日志在解压目录下的 .local\，不会影响 NAS 上的部署
- 不要把 NAS 网络映射盘写进 MEDIA_ROOTS，除非明确要在本机处理 NAS 文件
- 不要删除 vendor\ffmpeg 目录

四、常见问题
------------
Q: 提示缺少 Python？
A: 安装 3.10–3.12 并勾选加入 PATH，重新打开 cmd 后再点 start-local.cmd

Q: 提示 MEDIA_ROOTS 路径不存在 / 无法扫描？
A: 编辑项目根目录的 .env.local（首次启动后由模板生成），改成真实存在的本地目录

Q: 端口被占用？
A: 修改 .env.local 里的 LOCAL_WEB_PORT，或先 stop-local.cmd 再启动

Q: 强制停止？
A: powershell -ExecutionPolicy Bypass -File scripts\stop_local.ps1 -Force
EOF

# Exclude runtime artifacts if any leaked
find "${STAGING}" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "${STAGING}" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
rm -rf "${STAGING}/.venv" "${STAGING}/.local" "${STAGING}/.env.local" 2>/dev/null || true

echo "==> Creating ${ZIP_PATH}"
rm -f "${ZIP_PATH}"
(
  cd "${DIST_ROOT}"
  # Store as media-workbench-web-local/... inside the zip
  python3 - <<'PY' "${STAGING}" "${ZIP_PATH}"
import pathlib, sys, zipfile
staging = pathlib.Path(sys.argv[1])
zip_path = pathlib.Path(sys.argv[2])
base = staging.name
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for path in sorted(staging.rglob("*")):
        if path.is_file():
            arc = f"{base}/{path.relative_to(staging).as_posix()}"
            zf.write(path, arcname=arc)
print(zip_path)
print("files:", sum(1 for _ in staging.rglob("*") if _.is_file()))
PY
)

# Write a small pointer file
cat > "${DIST_ROOT}/LATEST_LOCAL_DIST.txt" <<EOF
${ZIP_NAME}
version=${VERSION}
built=$(date -Iseconds)
ffmpeg_src=${FFMPEG_SRC}
EOF

ls -lh "${ZIP_PATH}"
echo "DONE: ${ZIP_PATH}"
