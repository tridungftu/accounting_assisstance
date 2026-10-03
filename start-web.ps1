[CmdletBinding()]
param(
    [string]$PythonExecutable,
    [ValidateRange(1, 65535)][int]$Port = 8766,
    [string]$DataRoot,
    [string]$ConfigPath,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
if (-not $DataRoot) { $DataRoot = Join-Path $PSScriptRoot 'var\web' }
if (-not $ConfigPath) { $ConfigPath = Join-Path $PSScriptRoot 'cau_hinh.toml' }
$kttConfig = [IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $kttConfig -PathType Leaf)) { throw ('Khong tim thay cau hinh: ' + $kttConfig) }
$kttRoot = [IO.Path]::GetFullPath($DataRoot)
$kttUrl = 'http://127.0.0.1:' + $Port
$kttHash = [Security.Cryptography.SHA256]::Create()
try {
    $kttRootId = [BitConverter]::ToString($kttHash.ComputeHash([Text.Encoding]::UTF8.GetBytes($kttRoot.ToLowerInvariant()))).Replace('-', '').ToLowerInvariant()
} finally { $kttHash.Dispose() }

function Get-KttHealth {
    try { Invoke-RestMethod -Uri ($kttUrl + '/api/health') -TimeoutSec 1 -ErrorAction Stop } catch { $null }
}
function Assert-KttInstance($Health) {
    if ($Health.application -ne 'kho-tri-thuc-local' -or $Health.root_id -ne $kttRootId -or $Health.version -ne '0.3.0') {
        throw ('Cong ' + $Port + ' dang duoc mot ung dung/kho/phien ban khac su dung. Dung ung dung cu hoac chon -Port khac.')
    }
}

$kttHealth = Get-KttHealth
if ($null -ne $kttHealth) {
    Assert-KttInstance $kttHealth
} else {
    if (-not $PythonExecutable) {
        $kttBundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        if (Test-Path -LiteralPath $kttBundled) { $PythonExecutable = $kttBundled } else {
            $kttCommand = Get-Command python -ErrorAction SilentlyContinue
            if ($kttCommand) { $PythonExecutable = $kttCommand.Source }
        }
    }
    if (-not $PythonExecutable -or -not (Test-Path -LiteralPath $PythonExecutable)) {
        throw 'Can Python 3.11+ va openpyxl. Dung -PythonExecutable voi duong dan python.exe.'
    }
    & $PythonExecutable -X utf8 -c 'import sys, openpyxl; assert sys.version_info >= (3, 11)'
    if ($LASTEXITCODE -ne 0) { throw 'Python chua san sang. Can Python 3.11+ va openpyxl 3.1.x.' }
    New-Item -ItemType Directory -Path $kttRoot -Force | Out-Null
    $kttOut = Join-Path $kttRoot 'server-out.log'
    $kttErr = Join-Path $kttRoot 'server-error.log'
    $kttArguments = @('-X', 'utf8', '-m', 'kho_tri_thuc.giao_dien.server', '--config', ('"' + $kttConfig + '"'), '--root', ('"' + $kttRoot + '"'), '--port', $Port, '--no-browser')
    $kttPreviousPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
        $kttProcess = Start-Process -FilePath $PythonExecutable -ArgumentList $kttArguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $kttOut -RedirectStandardError $kttErr -PassThru
    } finally { $env:PYTHONPATH = $kttPreviousPath }
    for ($kttAttempt = 0; $kttAttempt -lt 30; $kttAttempt++) {
        $kttHealth = Get-KttHealth
        if ($null -ne $kttHealth) { break }
        $kttProcess.Refresh()
        if ($kttProcess.HasExited) { throw ('Khong mo duoc ung dung. Xem log: ' + $kttErr) }
        Start-Sleep -Milliseconds 200
    }
    if ($null -eq $kttHealth) { throw ('Chua ket noi duoc ung dung. Xem log: ' + $kttErr) }
    Assert-KttInstance $kttHealth
}
Write-Output ('Kho tri thuc: ' + $kttUrl)
Write-Output ('Thu muc du lieu: ' + $kttRoot)
Write-Output ('Cau hinh: ' + $kttConfig)
if (-not $NoBrowser) { Start-Process $kttUrl }
