[CmdletBinding()]
param([string]$PythonExecutable, [ValidateSet('sqlite', 'postgres')][string]$Engine = 'sqlite')
# V13: .\test.ps1 -Engine postgres chạy cùng bộ test trên PostgreSQL (cần .env có KHO_PG_DSN_TEST; tạo CSDL tạm rồi xóa)

$ErrorActionPreference = 'Stop'
if (-not $PythonExecutable) {
    $kttPythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $PythonExecutable = if ($kttPythonCommand) { $kttPythonCommand.Source } else {
        Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    }
}
if (-not (Test-Path -LiteralPath $PythonExecutable)) {
    throw 'Can Python 3.11+ va openpyxl. Truyen -PythonExecutable voi duong dan python.exe.'
}
$kttPreviousPythonPath = $env:PYTHONPATH
$kttTestExit = 1
try {
    $env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
    if ($Engine -eq 'postgres' -and -not $env:KHO_PG_DSN_TEST) {
        $kttEnvFile = Join-Path $PSScriptRoot '.env'
        if (Test-Path -LiteralPath $kttEnvFile) {
            [IO.File]::ReadAllLines($kttEnvFile) | Where-Object { $_ -match '^\s*KHO_PG_DSN_TEST\s*=\s*(.*)$' } | ForEach-Object { $env:KHO_PG_DSN_TEST = $Matches[1].Trim('"') }
        }
        if (-not $env:KHO_PG_DSN_TEST) { throw 'Chay -Engine postgres can KHO_PG_DSN_TEST trong .env (CÀI POSTGRESQL.cmd tao san).' }
    }
    $kttReport = if ($Engine -eq 'postgres') { 'var\test-results\latest-postgres.json' } else { 'var\test-results\latest.json' }
    & $PythonExecutable -X utf8 (Join-Path $PSScriptRoot 'tests\run_suite.py') --engine $Engine --report (Join-Path $PSScriptRoot $kttReport)
    $kttTestExit = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $kttPreviousPythonPath
}
exit $kttTestExit
