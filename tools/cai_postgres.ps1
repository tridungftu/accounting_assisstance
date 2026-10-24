<#
.SYNOPSIS
  V13 bước 2 — cài PostgreSQL 16 trên máy Windows và khởi tạo CSDL kho_tri_thuc (bấm nút, không gõ lệnh).
  Chạy qua "CÀI POSTGRESQL.cmd" (tự xin quyền quản trị — Windows hỏi "Yes" một lần).

.NOTES
  - Mật khẩu sinh ngẫu nhiên, ghi vào .env cạnh thư mục phần mềm (ngoài git), KHÔNG in ra màn hình, không ghi vào log.
  - Mật khẩu superuser dùng lúc cài chỉ là TẠM (có thể lọt vào log của winget) — sau khi dịch vụ chạy, đổi ngay sang mật khẩu thật qua stdin.
  - Chỉ nghe 127.0.0.1 (mặc định của bộ cài). Cổng 5432.
  - Chạy lại an toàn: bước nào đã xong thì bỏ qua. Không đụng kho thật (SQLite).
  - Phần mềm kết nối bằng vai trò app_ke_toan (KHO_PG_DSN); migration và bộ chuyển dùng chủ CSDL kho_app (KHO_PG_DSN_ADMIN).
#>
[CmdletBinding()]
param(
    [string]$PgVersion = '16',
    [int]$Port = 5432,
    [string]$DbName = 'kho_tri_thuc',
    [string]$PythonExecutable
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root '.env'
$log = Join-Path $root 'var\v13\cai-postgres.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
function Ghi([string]$m) { $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"; Write-Host $line; [IO.File]::AppendAllText($log, $line + "`r`n", $utf8NoBom) }
function MatKhau { -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ }) }
function DocEnv { $h = @{}; if (Test-Path $envFile) { [IO.File]::ReadAllLines($envFile) | Where-Object { $_ -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)$' } | ForEach-Object { $h[$Matches[1]] = $Matches[2].Trim('"') } }; $h }
function GhiEnv($h) { $lines = @($h.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Value)" }); [IO.File]::WriteAllLines($envFile, $lines, $utf8NoBom) }  # không BOM (review C2)
function Psql([string]$db, [string]$sql, [string]$pw) {
    # Chạy SQL qua stdin, không qua dòng lệnh; lỗi không ghi câu lệnh vào server log (review N7)
    $env:PGPASSWORD = $pw
    try {
        $full = "SET log_min_error_statement = panic;`n" + $sql
        $out = $full | & "$script:bin\psql.exe" -h 127.0.0.1 -p $Port -U postgres -d $db -v ON_ERROR_STOP=1 -q -X 2>&1
        if ($LASTEXITCODE -ne 0) { throw "psql lỗi (mã $LASTEXITCODE): $($out -join ' ' | ForEach-Object { $_.Substring(0, [Math]::Min(200, $_.Length)) })" }
        return $out
    } finally { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
}

Ghi "=== Bắt đầu cài PostgreSQL $PgVersion ==="
$envVars = DocEnv

# 1) Tìm hoặc cài PostgreSQL
$pgBin = Get-ChildItem "C:\Program Files\PostgreSQL\$PgVersion\bin\psql.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
$superTam = $null
if (-not $pgBin) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Máy không có winget (App Installer). Cài App Installer từ Microsoft Store rồi chạy lại.' }
    $superTam = MatKhau   # mật khẩu TẠM chỉ để cài; đổi ngay sau khi dịch vụ chạy
    Ghi 'Đang cài PostgreSQL bằng winget (vài phút, không cần bấm gì thêm)...'
    # Một chuỗi duy nhất, tự bọc ngoặc kép cho --override (review C1)
    $wingetArgs = "install -e --id PostgreSQL.PostgreSQL.$PgVersion --silent --accept-package-agreements --accept-source-agreements --override `"--mode unattended --unattendedmodeui none --superpassword $superTam --serverport $Port --servicename postgresql-x64-$PgVersion`""
    $p = Start-Process -FilePath 'winget' -ArgumentList $wingetArgs -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) { throw "winget trả mã lỗi $($p.ExitCode). Xem $log." }
    $pgBin = Get-ChildItem "C:\Program Files\PostgreSQL\$PgVersion\bin\psql.exe" | Select-Object -First 1
    Ghi 'Cài xong PostgreSQL.'
} else {
    Ghi "Đã có PostgreSQL tại $($pgBin.DirectoryName)."
    if (-not $envVars['KHO_PG_SUPER_PASSWORD']) { throw 'PostgreSQL đã cài trước đó nhưng .env chưa có KHO_PG_SUPER_PASSWORD. Ghi mật khẩu postgres vào .env rồi chạy lại.' }
}
$script:bin = $pgBin.DirectoryName

# 2) Chờ dịch vụ
$ok = $false
for ($i = 0; $i -lt 30 -and -not $ok; $i++) { & "$bin\pg_isready.exe" -h 127.0.0.1 -p $Port *> $null; if ($LASTEXITCODE -eq 0) { $ok = $true } else { Start-Sleep 2 } }
if (-not $ok) { throw "Dịch vụ PostgreSQL chưa sẵn sàng ở cổng $Port. Xem $log." }
Ghi "pg_isready đạt (cổng $Port)."

# 2b) Đổi mật khẩu superuser tạm → thật (qua stdin), ghi .env
if ($superTam) {
    $superThat = MatKhau
    Psql 'postgres' "ALTER ROLE postgres PASSWORD '$superThat';" $superTam | Out-Null
    $envVars['KHO_PG_SUPER_PASSWORD'] = $superThat
    GhiEnv $envVars
    Ghi 'Đã đổi mật khẩu superuser sang mật khẩu thật (mật khẩu tạm coi như đã lộ, không dùng nữa).'
}
$super = $envVars['KHO_PG_SUPER_PASSWORD']

# 3) Vai trò + CSDL (UTF-8, ICU vi)
foreach ($role in 'kho_app', 'app_ke_toan', 'app_cong_ai', 'app_doc') {
    $key = 'KHO_PG_PW_' + $role.ToUpper()
    if (-not $envVars[$key]) { $envVars[$key] = MatKhau }
}
GhiEnv $envVars
$sqlRoles = @"
DO `$`$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='kho_app') THEN CREATE ROLE kho_app LOGIN PASSWORD '$($envVars['KHO_PG_PW_KHO_APP'])'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_ke_toan') THEN CREATE ROLE app_ke_toan LOGIN PASSWORD '$($envVars['KHO_PG_PW_APP_KE_TOAN'])'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_cong_ai') THEN CREATE ROLE app_cong_ai LOGIN PASSWORD '$($envVars['KHO_PG_PW_APP_CONG_AI'])'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_doc') THEN CREATE ROLE app_doc LOGIN PASSWORD '$($envVars['KHO_PG_PW_APP_DOC'])'; END IF;
END `$`$;
"@
Psql 'postgres' $sqlRoles $super | Out-Null
$exists = (Psql 'postgres' "SELECT 1 FROM pg_database WHERE datname='$DbName';" $super) -join ''
if ($exists -notmatch '1') {
    $create = "CREATE DATABASE $DbName OWNER kho_app ENCODING 'UTF8' TEMPLATE template0 LOCALE_PROVIDER icu ICU_LOCALE 'vi' LOCALE 'C';"
    try { Psql 'postgres' $create $super | Out-Null }
    catch {
        Ghi 'Không tạo được CSDL với ICU vi — dùng collation C (ghi vào docs/QUYET-DINH.md).'
        Psql 'postgres' "CREATE DATABASE $DbName OWNER kho_app ENCODING 'UTF8' TEMPLATE template0 LC_COLLATE 'C' LC_CTYPE 'C';" $super | Out-Null
    }
    Ghi "Đã tạo CSDL $DbName (chủ: kho_app)."
} else { Ghi "CSDL $DbName đã có." }
Psql $DbName "CREATE EXTENSION IF NOT EXISTS unaccent; CREATE EXTENSION IF NOT EXISTS pg_trgm; CREATE EXTENSION IF NOT EXISTS pgcrypto; GRANT CONNECT ON DATABASE $DbName TO app_ke_toan, app_cong_ai, app_doc;" $super | Out-Null
$envVars['KHO_PG_DSN'] = "postgresql://app_ke_toan:$($envVars['KHO_PG_PW_APP_KE_TOAN'])@127.0.0.1:$Port/$DbName"
$envVars['KHO_PG_DSN_ADMIN'] = "postgresql://kho_app:$($envVars['KHO_PG_PW_KHO_APP'])@127.0.0.1:$Port/$DbName"
$envVars['KHO_PG_DSN_TEST'] = "postgresql://postgres:$super@127.0.0.1:$Port/postgres"
GhiEnv $envVars
Ghi "Đã ghi KHO_PG_DSN / KHO_PG_DSN_ADMIN / KHO_PG_DSN_TEST vào .env (không in ra màn hình)."

# 4) Thư viện Python psycopg + migration (chạy bằng chủ CSDL kho_app)
if (-not $PythonExecutable) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    $PythonExecutable = if ($cmd) { $cmd.Source } else { Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' }
}
if (-not (Test-Path -LiteralPath $PythonExecutable)) { throw 'Không tìm thấy Python 3.11+. Truyền -PythonExecutable.' }
Ghi "Dùng Python: $PythonExecutable"
& $PythonExecutable -m pip install --quiet --disable-pip-version-warning "psycopg[binary]>=3.1,<4"
if ($LASTEXITCODE -ne 0) { throw 'Cài psycopg thất bại (cần mạng tới PyPI).' }
$env:PYTHONPATH = Join-Path $root 'src'
& $PythonExecutable -X utf8 (Join-Path $root 'tools\khoi_tao_pg.py') --env $envFile --admin
if ($LASTEXITCODE -ne 0) { throw 'Migration PostgreSQL thất bại.' }
Ghi "=== Xong. Bước tiếp: 'CHUYỂN DỮ LIỆU SANG POSTGRESQL (kho thử).cmd' ==="
