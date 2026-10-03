[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$PythonExecutable,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArguments
)

$ErrorActionPreference = 'Stop'
if (-not $PythonExecutable) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $PythonExecutable = $pythonCommand.Source
    } else {
        $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        if (Test-Path -LiteralPath $bundledPython) {
            $PythonExecutable = $bundledPython
        } else {
            throw 'Can Python 3.11+. Truyen -PythonExecutable voi duong dan python.exe.'
        }
    }
}

$previousPythonPath = $env:PYTHONPATH
$appExitCode = 1
try {
    $sourcePath = Join-Path $PSScriptRoot 'src'
    $env:PYTHONPATH = if ($previousPythonPath) { $sourcePath + [IO.Path]::PathSeparator + $previousPythonPath } else { $sourcePath }
    & $PythonExecutable -X utf8 -m kho_tri_thuc --config (Join-Path $PSScriptRoot 'cau_hinh.toml') @AppArguments
    $appExitCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
exit $appExitCode
