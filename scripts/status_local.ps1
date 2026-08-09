. (Join-Path $PSScriptRoot "local_common.ps1")

Initialize-LocalDirectories
$config = Get-LocalConfiguration
$webProcessId = Get-ManagedProcessId "web"
$workerProcessId = Get-ManagedProcessId "worker"
$webPort = [int]$config["LOCAL_WEB_PORT"]

Write-Host "Web PID：$(if ($null -eq $webProcessId) { '未运行' } else { $webProcessId })"
Write-Host "Worker PID：$(if ($null -eq $workerProcessId) { '未运行' } else { $workerProcessId })"
Write-Host "本地地址：http://127.0.0.1:$webPort"
Write-Host "允许访问：$($config['MEDIA_ROOTS'])"
Write-Host "状态目录：$StateRoot"
try {
    $health = Get-LocalJson "http://127.0.0.1:$webPort/health"
    Write-Host "健康状态：$($health.status)；Worker：$($health.worker_alive)；版本：$($health.version)"
    if ($health.status -ne "ok" -or -not $health.worker_alive) { exit 1 }
} catch {
    Write-Host "健康状态：不可访问（$($_.Exception.Message)）"
    exit 1
}
