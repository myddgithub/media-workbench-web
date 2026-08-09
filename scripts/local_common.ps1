Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = Join-Path $ProjectRoot ".local"
$StateRoot = Join-Path $RuntimeRoot "state"
$RunRoot = Join-Path $RuntimeRoot "run"
$LogRoot = Join-Path $RuntimeRoot "logs"
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LocalConfigPath = Join-Path $ProjectRoot ".env.local"
$LocalConfigExamplePath = Join-Path $ProjectRoot ".env.local.example"

function Initialize-LocalDirectories {
    foreach ($path in @($RuntimeRoot, $StateRoot, $RunRoot, $LogRoot)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

function Get-LocalConfiguration {
    if (-not (Test-Path -LiteralPath $LocalConfigPath -PathType Leaf)) {
        if (-not (Test-Path -LiteralPath $LocalConfigExamplePath -PathType Leaf)) {
            throw "缺少本地配置模板：$LocalConfigExamplePath"
        }
        Copy-Item -LiteralPath $LocalConfigExamplePath -Destination $LocalConfigPath
        Write-Host "已创建本地配置：$LocalConfigPath"
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
}

function Assert-LocalPrerequisites([hashtable]$Config) {
    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        throw "缺少本地 Python 环境：$PythonExe"
    }
    foreach ($name in @("FFMPEG_BIN", "FFPROBE_BIN")) {
        if (-not (Test-Path -LiteralPath $Config[$name] -PathType Leaf)) {
            throw "本地配置中的 $name 不存在：$($Config[$name])"
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
