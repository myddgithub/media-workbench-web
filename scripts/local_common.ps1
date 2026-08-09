Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = Join-Path $ProjectRoot ".local"
$StateRoot = Join-Path $RuntimeRoot "state"
$RunRoot = Join-Path $RuntimeRoot "run"
$LogRoot = Join-Path $RuntimeRoot "logs"
$PortablePythonExe = Join-Path $ProjectRoot "vendor\python\python.exe"
$VenvPythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LocalConfigPath = Join-Path $ProjectRoot ".env.local"
$LocalConfigExamplePath = Join-Path $ProjectRoot ".env.local.example"
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"

# Prefer zero-dep portable runtime shipped in distribution zips.
if (Test-Path -LiteralPath $PortablePythonExe -PathType Leaf) {
    $PythonExe = $PortablePythonExe
    $PythonRuntimeKind = "portable"
} else {
    $PythonExe = $VenvPythonExe
    $PythonRuntimeKind = "venv"
}

function Initialize-LocalDirectories {
    foreach ($path in @($RuntimeRoot, $StateRoot, $RunRoot, $LogRoot)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

function Resolve-LocalPath([string]$PathText) {
    if ([string]::IsNullOrWhiteSpace($PathText)) {
        throw "路径不能为空"
    }
    $expanded = [Environment]::ExpandEnvironmentVariables($PathText.Trim())
    if ([System.IO.Path]::IsPathRooted($expanded)) {
        return [System.IO.Path]::GetFullPath($expanded)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $expanded))
}

function Get-LocalConfiguration {
    if (-not (Test-Path -LiteralPath $LocalConfigPath -PathType Leaf)) {
        if (-not (Test-Path -LiteralPath $LocalConfigExamplePath -PathType Leaf)) {
            throw "缺少本地配置模板：$LocalConfigExamplePath"
        }
        Copy-Item -LiteralPath $LocalConfigExamplePath -Destination $LocalConfigPath
        Write-Host "已创建本地配置：$LocalConfigPath"
        Write-Host "如本机盘符或目录不同，请编辑 MEDIA_ROOTS 后重新启动。"
    }

    $config = @{}
    foreach ($rawLine in Get-Content -LiteralPath $LocalConfigPath -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) { continue }
        $parts = $line.Split(@("="), 2, [System.StringSplitOptions]::None)
        if ($parts.Count -ne 2 -or -not $parts[0].Trim()) {
            throw "本地配置行无效：$rawLine"
        }
        $config[$parts[0].Trim()] = $parts[1].Trim()
    }

    foreach ($required in @("LOCAL_WEB_HOST", "LOCAL_WEB_PORT", "MEDIA_ROOTS", "FFMPEG_BIN", "FFPROBE_BIN")) {
        if (-not $config.ContainsKey($required) -or -not $config[$required]) {
            throw "本地配置缺少 $required"
        }
    }

    $config["FFMPEG_BIN"] = Resolve-LocalPath $config["FFMPEG_BIN"]
    $config["FFPROBE_BIN"] = Resolve-LocalPath $config["FFPROBE_BIN"]
    return $config
}

function Set-LocalEnvironment([hashtable]$Config) {
    $env:APP_TITLE = "音视频与 TextGrid 处理工作台（本地版）"
    $env:MEDIA_ROOTS = $Config["MEDIA_ROOTS"]
    $env:STATE_DIR = $StateRoot
    $env:DATABASE_PATH = Join-Path $StateRoot "jobs.sqlite3"
    $env:FFMPEG_BIN = $Config["FFMPEG_BIN"]
    $env:FFPROBE_BIN = $Config["FFPROBE_BIN"]
    $env:JOB_POLL_SECONDS = "1"
    $env:PYTHONPATH = $ProjectRoot
    $env:NO_PROXY = "127.0.0.1,localhost"
    # Keep embeddable/portable runtime self-contained.
    if ($PythonRuntimeKind -eq "portable") {
        $env:PYTHONHOME = Split-Path -Parent $PythonExe
        $env:PYTHONNOUSERSITE = "1"
    }
}

function Get-SystemPythonCandidates {
    $candidates = New-Object System.Collections.Generic.List[string]
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        foreach ($arg in @("-3.12", "-3.11", "-3.10", "-3")) {
            try {
                $resolved = & $pyLauncher.Source $arg -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $resolved) {
                    $candidates.Add($resolved.Trim())
                }
            } catch {
                # Try next launcher argument.
            }
        }
    }
    foreach ($name in @("python.exe", "python3.exe")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source) {
            $candidates.Add($cmd.Source)
        }
    }
    return @($candidates | Select-Object -Unique)
}

function Test-PythonVersion([string]$Exe) {
    try {
        $raw = & $Exe -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $raw) { return $false }
        $parts = $raw.Trim().Split(".")
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        return ($major -eq 3 -and $minor -ge 10 -and $minor -lt 14)
    } catch {
        return $false
    }
}

function Find-SystemPython {
    foreach ($candidate in Get-SystemPythonCandidates) {
        if (Test-PythonVersion $candidate) {
            return $candidate
        }
    }
    return $null
}

function Test-LocalPythonImports {
    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        return $false
    }
    $prevHome = $env:PYTHONHOME
    $prevNoUser = $env:PYTHONNOUSERSITE
    try {
        if ($PythonRuntimeKind -eq "portable") {
            $env:PYTHONHOME = Split-Path -Parent $PythonExe
            $env:PYTHONNOUSERSITE = "1"
        }
        & $PythonExe -c "import fastapi, uvicorn, pydantic, textgrid" 2>$null
        return ($LASTEXITCODE -eq 0)
    } finally {
        if ($null -eq $prevHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $prevHome }
        if ($null -eq $prevNoUser) { Remove-Item Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue } else { $env:PYTHONNOUSERSITE = $prevNoUser }
    }
}

function Ensure-LocalPythonEnvironment {
    # Zero-dep distribution: portable runtime is already complete.
    if ($PythonRuntimeKind -eq "portable") {
        if (-not (Test-LocalPythonImports)) {
            throw "便携 Python 运行时损坏或不完整：$PythonExe。请重新解压完整分发包（勿删 vendor\python）。"
        }
        return
    }

    $marker = Join-Path $ProjectRoot ".venv\.requirements.sha256"
    $currentHash = $null
    if (Test-Path -LiteralPath $RequirementsPath -PathType Leaf) {
        $currentHash = (Get-FileHash -LiteralPath $RequirementsPath -Algorithm SHA256).Hash
    }

    if ((Test-Path -LiteralPath $PythonExe -PathType Leaf) -and $currentHash) {
        if ((Test-Path -LiteralPath $marker -PathType Leaf) -and
            ((Get-Content -LiteralPath $marker -Raw).Trim() -eq $currentHash)) {
            return
        }
        # Existing venv from older installs: accept it if imports work, then write marker.
        if ((-not (Test-Path -LiteralPath $marker -PathType Leaf)) -and (Test-LocalPythonImports)) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $marker) -Force | Out-Null
            [System.IO.File]::WriteAllText($marker, $currentHash)
            return
        }
    } elseif ((Test-Path -LiteralPath $PythonExe -PathType Leaf) -and -not $currentHash) {
        return
    }

    $setupScript = Join-Path $PSScriptRoot "setup_local.ps1"
    if (-not (Test-Path -LiteralPath $setupScript -PathType Leaf)) {
        throw "缺少本地环境安装脚本：$setupScript。开发机请保留 scripts\setup_local.ps1；分发包应使用 vendor\python。"
    }
    Write-Host "正在准备本地 Python 环境（首次启动或依赖变更时会执行）..."
    & $setupScript
    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        throw "本地 Python 环境安装后仍缺少：$PythonExe"
    }
}

function Assert-LocalPrerequisites([hashtable]$Config) {
    Ensure-LocalPythonEnvironment
    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        throw "缺少本地 Python 环境：$PythonExe。开发机请安装 Python 3.10–3.12 后启动；分发包请确认 vendor\python 完整。"
    }
    foreach ($name in @("FFMPEG_BIN", "FFPROBE_BIN")) {
        if (-not (Test-Path -LiteralPath $Config[$name] -PathType Leaf)) {
            throw "本地配置中的 $name 不存在：$($Config[$name])。若使用分发包，请确认 vendor\ffmpeg 目录完整。"
        }
    }
}

function Get-PidFile([string]$Role) {
    return Join-Path $RunRoot "$Role.pid"
}

function Get-ManagedProcessId([string]$Role) {
    $pidFile = Get-PidFile $Role
    if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) { return $null }
    $raw = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    $processId = 0
    if (-not [int]::TryParse($raw, [ref]$processId)) {
        Remove-Item -LiteralPath $pidFile -Force
        return $null
    }
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Remove-Item -LiteralPath $pidFile -Force
        return $null
    }
    try {
        if (-not $process.Path -or -not $process.Path.Equals($PythonExe, [System.StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $pidFile -Force
            return $null
        }
    } catch {
        Remove-Item -LiteralPath $pidFile -Force
        return $null
    }
    return $processId
}

function Save-ManagedProcessId([string]$Role, [int]$ProcessId) {
    [System.IO.File]::WriteAllText((Get-PidFile $Role), [string]$ProcessId)
}

function Stop-ManagedProcess([string]$Role) {
    $processId = Get-ManagedProcessId $Role
    if ($null -eq $processId) {
        Write-Host "$Role 未运行"
        return
    }
    & taskkill.exe /PID $processId /T /F | Out-Null
    Remove-Item -LiteralPath (Get-PidFile $Role) -Force -ErrorAction SilentlyContinue
    Write-Host "已停止 $Role（PID $processId）"
}

function Get-LocalJson([string]$Url) {
    $client = New-Object System.Net.WebClient
    try {
        $client.Proxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy()
        return ($client.DownloadString($Url) | ConvertFrom-Json)
    } finally {
        $client.Dispose()
    }
}
