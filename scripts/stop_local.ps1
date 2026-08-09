param(
    [switch]$Force
)

. (Join-Path $PSScriptRoot "local_common.ps1")

Initialize-LocalDirectories
$config = Get-LocalConfiguration
$webPort = [int]$config["LOCAL_WEB_PORT"]
$webProcessId = Get-ManagedProcessId "web"

if ($null -ne $webProcessId -and -not $Force) {
    try {
        $jobs = @(Get-LocalJson "http://127.0.0.1:$webPort/api/jobs?limit=200")
        $active = @($jobs | Where-Object { $_.status -in @("running", "cancelling") })
        if ($active.Count -gt 0) {
            $ids = ($active | ForEach-Object { $_.id }) -join ", "
            throw "仍有运行中任务：$ids。请等待完成，或使用 -Force 明确强制停止。"
        }
    } catch {
        if ($_.Exception.Message -like "仍有运行中任务：*") { throw }
        Write-Warning "无法查询任务状态，将只停止已登记的本地进程：$($_.Exception.Message)"
    }
}

Stop-ManagedProcess "worker"
Stop-ManagedProcess "web"
Write-Host "本地工作台已停止；NAS 版不受影响。"
