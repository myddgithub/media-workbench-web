param(
    [switch]$NoBrowser
)

. (Join-Path $PSScriptRoot "local_common.ps1")

Initialize-LocalDirectories
$config = Get-LocalConfiguration
Assert-LocalPrerequisites $config
Set-LocalEnvironment $config

$webHost = $config["LOCAL_WEB_HOST"]
$webPort = [int]$config["LOCAL_WEB_PORT"]
if ($webHost -ne "127.0.0.1" -and $webHost -ne "localhost") {
    throw "本地版只允许监听 127.0.0.1 或 localhost，当前为：$webHost"
}

$webProcessId = Get-ManagedProcessId "web"
$workerProcessId = Get-ManagedProcessId "worker"
$listener = Get-NetTCPConnection -LocalPort $webPort -State Listen -ErrorAction SilentlyContinue
if ($listener -and $null -eq $webProcessId) {
    throw "端口 $webPort 已被其他程序占用（PID $($listener.OwningProcess -join ', ')）"
}

$startedRoles = [System.Collections.Generic.List[string]]::new()
try {
    if ($null -eq $webProcessId) {
        $webOut = Join-Path $LogRoot "web.out.log"
        $webErr = Join-Path $LogRoot "web.err.log"
        $web = Start-Process -FilePath $PythonExe -WorkingDirectory $ProjectRoot `
            -ArgumentList @("-u", "-m", "uvicorn", "app.main:app", "--host", $webHost, "--port", [string]$webPort) `
            -WindowStyle Hidden -RedirectStandardOutput $webOut -RedirectStandardError $webErr -PassThru
        Save-ManagedProcessId "web" $web.Id
        $webProcessId = $web.Id
        $startedRoles.Add("web")
    }

    if ($null -eq $workerProcessId) {
        $workerOut = Join-Path $LogRoot "worker.out.log"
        $workerErr = Join-Path $LogRoot "worker.err.log"
        $worker = Start-Process -FilePath $PythonExe -WorkingDirectory $ProjectRoot `
            -ArgumentList @("-u", "-m", "app.worker") -WindowStyle Hidden `
            -RedirectStandardOutput $workerOut -RedirectStandardError $workerErr -PassThru
        Save-ManagedProcessId "worker" $worker.Id
        $workerProcessId = $worker.Id
        $startedRoles.Add("worker")
    }

    $healthUrl = "http://${webHost}:$webPort/health"
    $healthy = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $health = Get-LocalJson $healthUrl
            if ($health.status -eq "ok" -and $health.worker_alive) {
                $healthy = $true
                break
            }
        } catch {
            # Web 或 worker 仍在启动。
        }
    }
    if (-not $healthy) {
        throw "本地 Web/Worker 未在 45 秒内进入健康状态，请查看 $LogRoot"
    }

    Write-Host "本地工作台已启动：http://${webHost}:$webPort"
    Write-Host "Web PID：$webProcessId；Worker PID：$workerProcessId"
    Write-Host "本地状态目录：$StateRoot"
    Write-Host "允许访问：$($config['MEDIA_ROOTS'])"
    if (-not $NoBrowser) {
        Start-Process "http://${webHost}:$webPort" | Out-Null
    }
} catch {
    foreach ($role in $startedRoles) {
        Stop-ManagedProcess $role
    }
    throw
}
