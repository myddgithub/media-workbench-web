# 音视频与 TextGrid 处理工作台

这是从 `MediaConverter` 和 `CutMergeExtractTools/CME-GUI_v4.py` 提取后端能力形成的独立
NAS Web 服务。它不替代两个桌面版，也不依赖语料库平台运行。

## 架构

- `app/main.py`：FastAPI 页面/API，只提交和查看任务。
- `app/worker.py`：唯一的后台任务消费者，执行高负载媒体处理。
- `app/store.py`：共享 SQLite 持久任务队列与日志。
- `app/paths.py`：NAS 根目录白名单和路径越界防护。
- `app/converter.py`：通用格式转换。
- `app/cme.py`：切分、合并、区间抽取的任务编排。
- `app/textgrid_ops.py`：从 CME-GUI v4 移植的 SG 边界、TextGrid 裁剪与累计时间轴算法。
- `app/media.py`：FFprobe、可取消 FFmpeg 子进程和原子输出。

不要把浏览器上传作为 NAS 大文件的主要入口；页面应直接选择白名单挂载目录。修改
TextGrid 时间逻辑时，必须同时增加覆盖边界、PointTier 和闭环合并的测试。
