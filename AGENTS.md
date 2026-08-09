# Project conventions

- This repository is private. Do not make the repository or its container package public.
- Keep the Web API and worker separate so FFmpeg load cannot block the UI process.
- All user paths must pass through `PathResolver`; never accept arbitrary host paths.
- Preserve the SG-nearest-boundary and TextGrid clipping/merge timing rules ported from CME-GUI v4.
- Publish media through temporary files and atomic rename; failed/cancelled jobs must not masquerade as complete output.
- Run `pytest -q` and the container health checks before deployment.
- The desktop `MediaConverter` and `CutMergeExtractTools` directories are reference implementations and must remain usable.
