[CmdletBinding()]
param([string]$PythonExecutable)

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
    & $PythonExecutable -X utf8 (Join-Path $PSScriptRoot 'tests\run_suite.py') --report (Join-Path $PSScriptRoot 'var\test-results\latest.json')
    $kttTestExit = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $kttPreviousPythonPath
}
exit $kttTestExit
