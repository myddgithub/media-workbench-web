# Build zero-dep Windows onedir exe for media-workbench-web.
# Run on Windows (or via powershell.exe from WSL).
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$FfmpegSrc = if ($env:FFMPEG_SRC) { $env:FFMPEG_SRC } else { "D:\mypy\MediaConverter\ffmpeg" }
if (-not (Test-Path -LiteralPath (Join-Path $FfmpegSrc "ffmpeg.exe"))) {
    throw "FFmpeg not found under $FfmpegSrc (set FFMPEG_SRC)"
}

$py = $null
foreach ($candidate in @(
    { py -3.12 -c "import sys; print(sys.executable)" },
    { py -3 -c "import sys; print(sys.executable)" },
    { python -c "import sys; print(sys.executable)" }
)) {
    try {
        $out = & $candidate 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            $py = $out.Trim()
            break
        }
    } catch {}
}
if (-not $py) { throw "Windows Python 3.10+ required to build exe" }
Write-Host "Using Python: $py"

& $py -m pip install -q --upgrade pip
& $py -m pip install -q -r (Join-Path $ProjectRoot "requirements.txt")
& $py -m pip install -q "pyinstaller>=6.3,<7"

$distRoot = Join-Path $ProjectRoot "dist"
$workRoot = Join-Path $ProjectRoot "build"
New-Item -ItemType Directory -Path $distRoot -Force | Out-Null

Write-Host "Running PyInstaller..."
& $py -m PyInstaller --noconfirm --clean `
    --distpath $distRoot `
    --workpath $workRoot `
    (Join-Path $ProjectRoot "MediaWorkbenchWeb.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$outDir = Join-Path $distRoot "MediaWorkbenchWeb"
if (-not (Test-Path -LiteralPath (Join-Path $outDir "MediaWorkbenchWeb.exe"))) {
    throw "Expected exe not found in $outDir"
}

# Bundle ffmpeg next to exe
$ffmpegDst = Join-Path $outDir "ffmpeg"
New-Item -ItemType Directory -Path $ffmpegDst -Force | Out-Null
Copy-Item -Force (Join-Path $FfmpegSrc "ffmpeg.exe") (Join-Path $ffmpegDst "ffmpeg.exe")
Copy-Item -Force (Join-Path $FfmpegSrc "ffprobe.exe") (Join-Path $ffmpegDst "ffprobe.exe")

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8)
}

# Portable config template for exe folder (no BOM — launcher also tolerates BOM)
Write-Utf8NoBom (Join-Path $outDir ".env.local.example") @"
# 本地版只监听当前电脑，不向局域网开放。
LOCAL_WEB_HOST=127.0.0.1
LOCAL_WEB_PORT=8768

# 按对方电脑修改盘符/目录（可用 D:/ 正斜杠，避免转义问题）
MEDIA_ROOTS=本机D盘=D:/

# 相对 exe 目录
FFMPEG_BIN=ffmpeg/ffmpeg.exe
FFPROBE_BIN=ffmpeg/ffprobe.exe
"@

Write-Utf8NoBom (Join-Path $outDir "使用说明.txt") @"
音视频与 TextGrid 处理工作台 — Windows 本地版（exe）
Media & TextGrid Workbench — Windows local edition (exe)
========================================================

【中文】
一、使用方法
1. 解压/复制整个 MediaWorkbenchWeb 文件夹到任意位置（不要只拷贝 exe）
2. 如有需要，编辑 .env.local（首次运行会自动生成）中的 MEDIA_ROOTS
3. 双击 MediaWorkbenchWeb.exe
4. 浏览器打开 http://127.0.0.1:8768
5. 页面右上角可切换 中文 / EN
6. 关闭黑色控制台窗口即停止服务
   或在本目录命令行运行：MediaWorkbenchWeb.exe --stop
   查看状态：MediaWorkbenchWeb.exe --status

二、说明
- 零依赖：无需安装 Python / FFmpeg
- 仅 Windows 10/11 x64
- 任务数据在本目录 .local\
- 请保持 ffmpeg\ 与 _internal\ 与 exe 同级

三、注意
- 杀毒软件可能拦截，请添加信任
- 不要把 NAS 映射盘写入 MEDIA_ROOTS，除非明确要在本机处理 NAS 文件

【English】
1. Keep the whole MediaWorkbenchWeb folder (do not copy only the .exe)
2. Edit MEDIA_ROOTS in .env.local if needed (created on first run)
3. Double-click MediaWorkbenchWeb.exe
4. Open http://127.0.0.1:8768
5. Use the top-right 中文 / EN switcher for UI language
6. Close the console window to stop, or run: MediaWorkbenchWeb.exe --stop
   Status: MediaWorkbenchWeb.exe --status

Notes: zero-dep (no Python/FFmpeg install); Windows 10/11 x64; job data in .local\;
keep ffmpeg\ and _internal\ next to the exe. Loopback only (127.0.0.1).
"@

# Convenience stop scripts (single-quoted so PowerShell does not expand %~dp0)
@(
    '@echo off',
    '"%~dp0MediaWorkbenchWeb.exe" --stop',
    'pause'
) | Set-Content -LiteralPath (Join-Path $outDir "停止服务.cmd") -Encoding ASCII
@(
    '@echo off',
    '"%~dp0MediaWorkbenchWeb.exe" --stop',
    'pause'
) | Set-Content -LiteralPath (Join-Path $outDir "stop.cmd") -Encoding ASCII

# Zip the onedir folder
$stamp = Get-Date -Format "yyyyMMdd"
$zipName = "MediaWorkbenchWeb-exe-v1.0.0-$stamp.zip"
$zipPath = Join-Path $distRoot $zipName
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }

Write-Host "Creating $zipPath ..."
Compress-Archive -Path $outDir -DestinationPath $zipPath -CompressionLevel Optimal

$exe = Get-Item (Join-Path $outDir "MediaWorkbenchWeb.exe")
Write-Host "DONE"
Write-Host "  Folder: $outDir"
Write-Host "  Exe:    $($exe.FullName) ($([math]::Round($exe.Length/1MB,1)) MB)"
Write-Host "  Zip:    $zipPath ($([math]::Round((Get-Item $zipPath).Length/1MB,1)) MB)"

Set-Content -LiteralPath (Join-Path $distRoot "LATEST_LOCAL_EXE.txt") -Encoding UTF8 -Value @(
    $zipName
    "folder=MediaWorkbenchWeb"
    "exe=MediaWorkbenchWeb.exe"
    "built=$(Get-Date -Format o)"
)
