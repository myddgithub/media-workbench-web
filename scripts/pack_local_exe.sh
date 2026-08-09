#!/usr/bin/env bash
# Wrapper: build Windows exe via powershell.exe (WSL / Git Bash).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if ! command -v powershell.exe >/dev/null 2>&1; then
  echo "ERROR: powershell.exe not found. Run scripts/pack_local_exe.ps1 on Windows." >&2
  exit 1
fi
WIN_SCRIPT="$(wslpath -w "$ROOT/scripts/pack_local_exe.ps1" 2>/dev/null || cygpath -w "$ROOT/scripts/pack_local_exe.ps1")"
# Optional FFMPEG_SRC passthrough
EXTRA=()
if [[ -n "${FFMPEG_SRC:-}" ]]; then
  if command -v wslpath >/dev/null 2>&1 && [[ "${FFMPEG_SRC}" == /mnt/* ]]; then
    export FFMPEG_SRC="$(wslpath -w "$FFMPEG_SRC")"
  fi
fi
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$WIN_SCRIPT"
