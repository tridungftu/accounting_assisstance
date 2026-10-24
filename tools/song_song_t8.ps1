# V13 bước 6 — so song song SQLite ↔ PostgreSQL trên bản sao tạm của kho thử T8; chỉ in số đếm.
[CmdletBinding()]
param([string]$PythonExecutable, [string]$ConfigPath)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $PythonExecutable) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    $PythonExecutable = if ($cmd) { $cmd.Source } else { Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' }
}
if (-not $ConfigPath) { $ConfigPath = Join-Path $root 'cau_hinh.thu-T8.toml' }
$envFile = Join-Path $root '.env'
if (-not (Test-Path $envFile)) { throw "Chưa có .env — chạy 'CÀI POSTGRESQL.cmd' trước." }
$env:KHO_ENV_FILE = $envFile
$env:PYTHONPATH = Join-Path $root 'src'
& $PythonExecutable -X utf8 (Join-Path $root 'tools\song_song_t8.py') --config $ConfigPath --dsn-key KHO_PG_DSN_ADMIN
$code = $LASTEXITCODE
Write-Host "Báo cáo: var\v13\song-song-T8.md (mã thoát $code; 0 = giống từng dòng)"
exit $code
