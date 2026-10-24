# V13 bước 4 — chép kho thật ra bản sao rồi chuyển sang PostgreSQL (CSDL trong .env). Kho thật SQLite không bị đụng.
[CmdletBinding()]
param([string]$PythonExecutable)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $PythonExecutable) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    $PythonExecutable = if ($cmd) { $cmd.Source } else { Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' }
}
$envFile = Join-Path $root '.env'
if (-not (Test-Path $envFile)) { throw "Chưa có .env — chạy 'CÀI POSTGRESQL.cmd' trước." }
[IO.File]::ReadAllLines($envFile) | Where-Object { $_ -match '^\s*KHO_PG_DSN_ADMIN\s*=\s*(.*)$' } | ForEach-Object { $env:KHO_PG_DSN = $Matches[1].Trim('"') }
if (-not $env:KHO_PG_DSN) { throw '.env chưa có KHO_PG_DSN_ADMIN (chạy CÀI POSTGRESQL.cmd trước).' }
$src = Join-Path $root 'var\plhn-that\kho.sqlite'
$dst = Join-Path $root 'var\v13\kho-ban-sao.sqlite'
New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
$env:PYTHONPATH = Join-Path $root 'src'
& $PythonExecutable -X utf8 (Join-Path $root 'tools\sao_chep_sqlite.py') --nguon $src --dich $dst
if ($LASTEXITCODE -ne 0) { throw 'Sao chép kho SQLite thất bại.' }
& $PythonExecutable -X utf8 (Join-Path $root 'tools\chuyen_sqlite_sang_pg.py') --sqlite $dst --bao-cao (Join-Path $root 'var\v13\chuyen-doi.json')
$code = $LASTEXITCODE
Write-Host "Bảng đối chiếu K2: var\v13\chuyen-doi.md (mã thoát $code; 0 = mọi bảng khớp)"
# V13 bước 5: nạp kho thử T8 (bảng V12 nguyên trạng) vào schema v12_thu_t8 để mở bằng «MỞ PHẦN MỀM THỬ T8 (PostgreSQL).cmd»
& $PythonExecutable -X utf8 (Join-Path $root 'tools\tao_cau_hinh_pg.py')
$thu = Join-Path $root 'var\plhn-thu-T8\kho.sqlite'
if (Test-Path $thu) {
    $env:KHO_PG_DSN_ADMIN = $env:KHO_PG_DSN
    # Nạp MỘT LẦN: schema đã có thì giữ nguyên (không xóa việc anh đã làm trên PostgreSQL — review lần 2 #2)
    & $PythonExecutable -X utf8 (Join-Path $root 'tools\chep_v12_sang_pg.py') --sqlite $thu --schema v12_thu_t8 --grant app_ke_toan --bao-cao (Join-Path $root 'var\v13\chep-v12-thu-T8.json')
    $code2 = $LASTEXITCODE
    # Thư mục kho riêng cho bản PostgreSQL: chỉ chép tệp gốc raw\ (chứng từ đã nạp), không chép kho.sqlite
    $pgDir = Join-Path $root 'var\plhn-thu-T8-postgres'
    New-Item -ItemType Directory -Force -Path $pgDir | Out-Null
    $rawSrc = Join-Path $root 'var\plhn-thu-T8\raw'
    if (Test-Path $rawSrc) { robocopy $rawSrc (Join-Path $pgDir 'raw') /E /XC /XN /XO /NFL /NDL /NJH /NJS | Out-Null }
    Write-Host "Nạp kho thử T8 lên PostgreSQL (schema v12_thu_t8): mã thoát $code2 (0 = mọi bảng khớp; schema đã có thì giữ nguyên). Báo cáo: var\v13\chep-v12-thu-T8.json"
    if ($code2 -ne 0) { $code = $code2 }
} else {
    Write-Host 'Chưa có var\plhn-thu-T8\kho.sqlite — bỏ qua bước nạp kho thử T8 lên PostgreSQL.'
}
exit $code
