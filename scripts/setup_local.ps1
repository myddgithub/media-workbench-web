Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local_common.ps1")

Initialize-LocalDirectories

if (-not (Test-Path -LiteralPath $RequirementsPath -PathType Leaf)) {
    throw "缺少依赖清单：$RequirementsPath"
}

$systemPython = Find-SystemPython
if (-not $systemPython) {
    throw @"
未找到可用的 Python 3.10–3.12。
请先安装官方 Python（勾选 Add python.exe to PATH），然后重新运行 start-local.cmd。
下载：https://www.python.org/downloads/windows/
"@
}

$venvDir = Join-Path $ProjectRoot ".venv"
Write-Host "使用系统 Python：$systemPython"
Write-Host "创建/更新虚拟环境：$venvDir"
& $systemPython -m venv $venvDir
if ($LASTEXITCODE -ne 0) {
    throw "创建虚拟环境失败"
}

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "虚拟环境创建后缺少：$PythonExe"
}

Write-Host "安装依赖：$RequirementsPath"
& $PythonExe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "升级 pip 失败"
}
& $PythonExe -m pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "安装 requirements.txt 失败（请检查网络或代理）"
}

$hash = (Get-FileHash -LiteralPath $RequirementsPath -Algorithm SHA256).Hash
$marker = Join-Path $venvDir ".requirements.sha256"
[System.IO.File]::WriteAllText($marker, $hash)
Write-Host "本地 Python 环境已就绪。"
