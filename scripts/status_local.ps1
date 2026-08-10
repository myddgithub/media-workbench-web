. (Join-Path $PSScriptRoot "local_common.ps1")

Initialize-LocalDirectories
$config = Get-LocalConfiguration
$webProcessId = Get-ManagedProcessId "web"
$workerProcessId = Get-ManagedProcessId "worker"
$webPort = [int]$config["LOCAL_WEB_PORT"]

$webLabel = if ($null -eq $webProcessId) { "未运行 / not running" } else { "$webProcessId" }
$workerLabel = if ($null -eq $workerProcessId) { "未运行 / not running" } else { "$workerProcessId" }
Write-Host "Web PID: $webLabel"
Write-Host "Worker PID: $workerLabel"
Write-Host "本地地址 / Local URL: http://127.0.0.1:$webPort"
Write-Host "允许访问 / Allowed roots: $($config['MEDIA_ROOTS'])"
Write-Host "状态目录 / State: $StateRoot"
try {
    $health = Get-LocalJson "http://127.0.0.1:$webPort/health"
    Write-Host "健康状态 / Health: $($health.status); Worker: $($health.worker_alive); version: $($health.version)"
    if ($health.status -ne "ok" -or -not $health.worker_alive) { exit 1 }
} catch {
    Write-Host "健康状态 / Health: unreachable ($($_.Exception.Message))"
    exit 1
}
