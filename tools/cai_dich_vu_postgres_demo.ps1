<#
  Cai cum PostgreSQL DEMO (127.0.0.1:5432) thanh dich vu Windows "ktt-postgres-demo" - Anh chot 25/10/2026
  (su co: docs\46-chuyen-doi-dieu-phoi\SU-CO-POSTGRES-DEMO.md). Dich vu tu chay cung may, duoc Windows bao tat sach khi tat/cap nhat,
  khong phu thuoc Codex hay Claude. Chay MOT lan bang quyen quan tri (tep "CAI DICH VU POSTGRES DEMO.cmd" tu xin quyen).
  Khong tao cum moi, khong xoa du lieu, khong chay SQL: chi dung cum dang chay tay (tat sach), cap quyen thu muc cho
  NT AUTHORITY\NetworkService, dang ky dich vu bang pg_ctl register, khoi dong va cho cong 5432.
#>
$ErrorActionPreference = 'Stop'
$goc = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)          # D:\Claude\Phan mem ho tro ke toan
$runtime = Join-Path $goc 'var\postgresql16-16.15-runtime'
$pgctl = Join-Path $runtime 'bin\pg_ctl.exe'
$data = Join-Path $goc 'var\postgresql-ktt-16\data'
$ten = 'ktt-postgres-demo'
$nhatKy = Join-Path $goc ('var\pg-dich-vu-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
function Bao([string]$s) { Write-Host $s; Add-Content -LiteralPath $nhatKy -Value ((Get-Date -Format 's') + ' ' + $s) }
function Cong5432 { (Test-NetConnection -ComputerName 127.0.0.1 -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue) }

$laQuanTri = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $laQuanTri) { Write-Host 'Can quyen quan tri: bam dup tep "CAI DICH VU POSTGRES DEMO.cmd" va chon Yes khi Windows hoi.'; exit 1 }
foreach ($p in @($pgctl, $data)) { if (-not (Test-Path -LiteralPath $p)) { Write-Host "Khong thay $p - dung lai, khong lam gi."; exit 1 } }

$sv = Get-Service -Name $ten -ErrorAction SilentlyContinue
if ($sv) {
    Bao "Dich vu $ten da co (trang thai: $($sv.Status), khoi dong: $($sv.StartType))."
    if ($sv.Status -ne 'Running') { Start-Service -Name $ten; Bao 'Da khoi dong dich vu.' }
    exit 0
}

# 1. Tat sach cum dang chay tay (neu co) - che do fast: cho giao dich xong, ghi checkpoint, khong can phuc hoi lai
& $pgctl status -D $data *> $null
if ($LASTEXITCODE -eq 0) {
    Bao 'Dang tat sach cum PostgreSQL DEMO dang chay tay (cac trang DEMO se mat ket noi vai giay)...'
    & $pgctl stop -D $data -m fast -w -t 600
    if ($LASTEXITCODE -ne 0) { Bao 'Khong tat duoc cum trong 10 phut - dung lai, khong dang ky dich vu.'; exit 1 }
    Bao 'Da tat sach.'
}

# 2. Cap quyen cho tai khoan dich vu NetworkService (SID S-1-5-20): sua thu muc du lieu, doc/chay thu muc chuong trinh
Bao 'Dang cap quyen thu muc cho dich vu (co the mat vai phut vi nhieu tep)...'
& icacls $data /grant '*S-1-5-20:(OI)(CI)M' /T /Q | Out-Null
& icacls $runtime /grant '*S-1-5-20:(OI)(CI)RX' /T /Q | Out-Null

# 3. Dang ky dich vu tu khoi dong; nhat ky PostgreSQL ghi vao data\log
& $pgctl register -N $ten -D $data -S auto -o '-h 127.0.0.1 -p 5432 -c logging_collector=on -c log_directory=log'
if ($LASTEXITCODE -ne 0) { Bao 'Dang ky dich vu that bai - cum chua chay; mo lai bang tay hoac bao lead.'; exit 1 }
Bao "Da dang ky dich vu $ten (tu khoi dong cung may)."

# 4. Khoi dong va cho cong 5432
Start-Service -Name $ten
$han = (Get-Date).AddMinutes(40)
while (-not (Cong5432) -and (Get-Date) -lt $han) { Start-Sleep -Seconds 5 }
if (Cong5432) { Bao 'Xong: PostgreSQL DEMO chay bang dich vu Windows, cong 5432 san sang.' }
else { Bao 'Dich vu da chay nhung cong 5432 chua mo sau 40 phut - xem data\log va bao lead.'; exit 1 }
Bao "Nhat ky: $nhatKy"
