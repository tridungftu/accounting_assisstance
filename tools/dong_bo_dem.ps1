# V13 — việc hằng đêm (anh chốt 17/10/2026): (1) phản chiếu kho thật SQLite → K2 (kho.*/nhat_ky, chạy lại không trùng);
# (2) sao lưu kho thử PostgreSQL (schema v12_thu_t8) ra file .sqlite, giữ 7 bản. Kho thật chỉ được ĐỌC (bản sao bằng backup API).
[CmdletBinding()]
param([string]$PythonExecutable)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root 'var\v13'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'dong-bo-dem.log'
function Ghi($msg) { $line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $msg; Add-Content -LiteralPath $log -Value $line -Encoding UTF8; Write-Host $line }
if (-not $PythonExecutable) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    $PythonExecutable = if ($cmd) { $cmd.Source } else { Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' }
}
$envFile = Join-Path $root '.env'
if (-not (Test-Path $envFile)) { Ghi 'Chưa có .env — bỏ qua (chưa cài PostgreSQL).'; exit 0 }
$env:KHO_ENV_FILE = $envFile
[IO.File]::ReadAllLines($envFile) | Where-Object { $_ -match '^\s*KHO_PG_DSN_ADMIN\s*=\s*(.*)$' } | ForEach-Object { $env:KHO_PG_DSN_ADMIN = $Matches[1].Trim('"') }
$env:PYTHONPATH = Join-Path $root 'src'
$code = 0
$src = Join-Path $root 'var\plhn-that\kho.sqlite'
$dst = Join-Path $root 'var\v13\kho-ban-sao-dem.sqlite'
if (Test-Path $src) {
    & $PythonExecutable -X utf8 (Join-Path $root 'tools\sao_chep_sqlite.py') --nguon $src --dich $dst | Out-Null
    if ($LASTEXITCODE -ne 0) { Ghi 'Sao chép kho thật thất bại.'; $code = 1 }
    else {
        $env:KHO_PG_DSN = $env:KHO_PG_DSN_ADMIN
        & $PythonExecutable -X utf8 (Join-Path $root 'tools\chuyen_sqlite_sang_pg.py') --sqlite $dst --bao-cao (Join-Path $logDir 'dong-bo-dem.json') | Out-Null
        $c1 = $LASTEXITCODE; Ghi "Phản chiếu kho thật → K2: mã thoát $c1 (0 = mọi bảng khớp; chi tiết var\v13\dong-bo-dem.md)"
        if ($c1 -ne 0) { $code = $c1 }
    }
}
$out = & $PythonExecutable -X utf8 (Join-Path $root 'tools\sao_luu_pg.py') --schema v12_thu_t8 --thu-muc (Join-Path $root 'var\sao-luu-pg') --giu 7
$c2 = $LASTEXITCODE; Ghi "Sao lưu kho thử PostgreSQL: mã thoát $c2 · $out"
if ($c2 -ne 0) { $code = $c2 }
exit $code
