# 音视频与 TextGrid 处理工作台

面向 NAS 的独立 Web 工具，把现有桌面版 `MediaConverter` 与
`CutMergeExtractTools/CME-GUI v4.0 Integrated` 的核心能力统一到一个后台任务系统中。
桌面版保持不变，Web 版直接处理 NAS 白名单目录中的文件，不要求先把大文件上传到浏览器。

## 功能

- **格式转换**：视频转音频、音频转码、视频转码、视频压缩；支持目录递归、并行文件、
  保留子目录、语料 WAV 16k 单声道预设，以及 Intel QSV 编码。
- **同步切分**：同步输出 MP4、WAV、TextGrid；支持固定目标时长和 CME-GUI v4 的
  “最近 SG 层边界”策略。
- **片段合并**：识别 `前缀_segNNN`，按编号合并；TextGrid 时长优先用于累计时间轴。
- **区间抽取**：按多行 `开始-结束` 时间同步抽取三件套。
- **后台任务**：持久队列、进度、日志、取消、失败状态、历史记录和结果链接。
- **安全路径**：只能访问 `MEDIA_ROOTS` 配置的挂载目录，拒绝绝对路径、`..` 和符号链接越界。
- **完整输出**：媒体先写临时文件，成功后原子发布；取消或失败不会留下伪装成成品的文件。

## 为什么是独立服务

Web API 与媒体 worker 分开运行。FFmpeg 转码满载或单个任务失败时，不会阻塞语料库平台
和本工具的页面。它可以独立升级、限流、停止和回滚；语料库平台只需提供入口或在后续通过
API 传递待处理路径。

## CME 算法兼容

`app/textgrid_ops.py` 保留桌面版已经验证过的关键规则：

1. 切分目标点前后分别查找 SG 有效区间边界，选择偏差最小者。
2. TextGrid 裁剪使用严格交集和 `1e-6` 容差，片段时间从 0 重新开始。
3. 合并时每段时长采用 TextGrid > 视频 > 音频的优先级。
4. IntervalTier 与 PointTier 均在切分和合并中平移。

媒体读写由容器内 FFmpeg 完成，避免桌面 GUI、MoviePy 和 pydub 与 Web worker 生命周期耦合。
视频切分/合并会重新编码为 H.264 + AAC；WAV 输出使用 PCM 16-bit。

## Windows 本地版

本地版和 NAS 版使用同一套代码，但进程、任务数据库、日志和媒体白名单完全独立。本机默认只开放
`D:\`，不会自动加入 NAS 网络映射盘；Web 只监听 `127.0.0.1`，局域网其他设备无法访问。

- 双击 `start-local.cmd`：启动独立的 Web 和媒体 Worker，并打开 `http://127.0.0.1:8768`。
- 双击 `status-local.cmd`：查看两个进程及健康状态。
- 双击 `stop-local.cmd`：没有运行中任务时安全停止；需要强制停止时运行
  `powershell -ExecutionPolicy Bypass -File scripts/stop_local.ps1 -Force`。

首次启动会从 `.env.local.example` 生成不纳入 Git 的 `.env.local`。可在其中修改本地白名单目录和
FFmpeg 路径；不要把 NAS 映射盘加入 `MEDIA_ROOTS`，除非明确要从本机处理 NAS 文件。本地任务库和
日志位于 `.local/`，NAS 上的 `/volume1/docker/media-workbench-web/state` 不受本地启停影响。

如需使用 Docker 做临时本机测试，仍可复制 `.env.example` 后运行 `docker compose up -d --build`；
Windows 日常使用优先采用上述脚本，直接复用 `MediaConverter` 中现有的 FFmpeg，避免重复下载镜像。

### 分发到其他 Windows 电脑（零依赖）

#### 方案 A：exe 目录包（推荐给最终用户）

在 Windows 或 WSL（可调用 `powershell.exe`）执行：

```bash
bash scripts/pack_local_exe.sh
# 或: powershell -ExecutionPolicy Bypass -File scripts/pack_local_exe.ps1
```

生成：

- 文件夹 `dist/MediaWorkbenchWeb/`（内含 `MediaWorkbenchWeb.exe`、`ffmpeg\`、`_internal\`）
- 压缩包 `dist/MediaWorkbenchWeb-exe-v*.zip`

对方：解压整个文件夹 → 双击 `MediaWorkbenchWeb.exe` → 浏览器
`http://127.0.0.1:8768`。关闭控制台窗口即停止；也可用 `MediaWorkbenchWeb.exe --stop`。
无需安装 Python / FFmpeg。

#### 方案 B：便携源码 + 内嵌 Python zip

```bash
bash scripts/pack_local_dist.sh
```

生成 `dist/media-workbench-web-local-v*-standalone.zip`（`vendor/python` + `vendor/ffmpeg` +
`start-local.cmd`）。同样零依赖，结构更透明，体积与 exe 包接近。

打包机需要 Windows 版 Python 3.12 与 PyInstaller（exe 方案）或 pip（standalone 方案）。
可选：`FFMPEG_SRC`、`HOST_WIN_PYTHON`、`PYTHON_VERSION`。

## 绿联 NAS 部署

本机当前规划：

- 程序目录：`/volume1/docker/media-workbench-web`
- 媒体目录：`/volume2/Mydata`
- Web 端口：`8768`
- Intel 核显：`/dev/dri`，容器追加宿主机 `video(44)`、`render(105)` 组

部署前在 NAS 上核对用户 ID：

```bash
id edwardcyd
cp .env.example .env
# 修改 .env 中的 PUID、PGID 和 NAS_MEDIA_PATH
bash scripts/deploy_nas.sh
```

如果 NAS 本地已有包含 Python 3.11、`ffmpeg` 和 `ffprobe` 的可信镜像，可以在 `.env`
中把它设为 `BASE_IMAGE` 并设置 `INSTALL_FFMPEG=0`，避免重复安装系统包。例如本机现有的
YouTube 下载服务镜像可作为构建缓存来源；GitHub Actions 仍使用默认值构建完整独立镜像。

访问 `http://192.168.1.2:8768`；远程访问使用 Tailscale 地址。该服务没有设计成公网文件站，
不要通过 Funnel、Cloudflare Tunnel 或路由器端口转发直接公开。

## 路径与文件行为

- 页面中的路径都是所选存储位置下的相对路径，例如 `下载/YouTube_videos`。
- 输出目录可以位于输入目录内；默认建议使用 `_segments`、`_merged`、`_extract`、`converted`。
- 默认不覆盖已有文件。勾选“覆盖已有结果”后，新文件仍先写临时文件，再替换旧结果。
- 合并默认启用配套文件严格检查。如果实际只有 WAV + TextGrid，应取消“视频 MP4”勾选，
  而不是关闭严格检查。
- 任务记录可以删除，但删除记录不会删除结果文件。

## 测试

```bash
pip install -r requirements-dev.txt
pytest -q
```

测试包括路径越界、任务状态机、转换参数、SG 边界、IntervalTier/PointTier 裁剪合并、API，
以及在检测到 FFmpeg 时执行一次真实音频转码。

## 回滚与数据

程序镜像可以按 Git 提交标签回滚。任务数据库保存在 `./state/jobs.sqlite3`，媒体结果始终位于
`/volume2/Mydata` 的用户指定目录。回滚镜像不会删除或回滚媒体文件。
