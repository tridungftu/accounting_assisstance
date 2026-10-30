# Tự khởi động lại phiên lead khi không còn phiên nào chạy (CD-037).
# Task Scheduler gọi 30 phút/lần. Lead coi là "còn sống" nếu var\lead-nhip.txt hoặc TRANG-THAI.md được sửa trong 45 phút gần nhất.
# Có khóa chống chạy trùng. Ghi nhật ký var\nhat-ky-tu-khoi-dong.log. Không đọc .env, không đụng kho thật.
param([int]$PhutSong = 45)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$nhatKy = Join-Path $repo 'var\nhat-ky-tu-khoi-dong.log'
$khoa = Join-Path $repo 'var\lead-tu-khoi-dong.lock'
$trangThai = Join-Path $repo 'docs\46-chuyen-doi-dieu-phoi\TRANG-THAI.md'
New-Item -ItemType Directory -Force (Split-Path $nhatKy) | Out-Null

function Ghi([string]$s) {
    Add-Content -LiteralPath $nhatKy -Encoding utf8 -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $s)
}

# Khóa: lượt tự khởi động trước còn chạy thì thôi.
if (Test-Path -LiteralPath $khoa) {
    $pidCu = (Get-Content -LiteralPath $khoa -Raw).Trim()
    if ($pidCu -and (Get-Process -Id ([int]$pidCu) -ErrorAction SilentlyContinue)) {
        Ghi "bo qua: luot truoc (pid $pidCu) con chay"
        exit 0
    }
}

# Lead còn sống: nhịp var\lead-nhip.txt (lead chạm mỗi lượt /loop) hoặc TRANG-THAI vừa được cập nhật.
$nhip = Join-Path $repo 'var\lead-nhip.txt'
$sua = (Get-Item -LiteralPath $trangThai).LastWriteTime
if (Test-Path -LiteralPath $nhip) {
    $suaNhip = (Get-Item -LiteralPath $nhip).LastWriteTime
    if ($suaNhip -gt $sua) { $sua = $suaNhip }
}
$phut = [int]((Get-Date) - $sua).TotalMinutes
if ($phut -lt $PhutSong) {
    Ghi "bo qua: TRANG-THAI sua $phut phut truoc, lead con song"
    exit 0
}

Set-Content -LiteralPath $khoa -Value $PID -Encoding ascii
try {
    Ghi "chay lead: TRANG-THAI sua $phut phut truoc"
    Push-Location -LiteralPath $repo
    $lenh = 'Doc docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md, lam mot luot theo CD-020 va cac muc MOI; cap nhat TRANG-THAI.md.'
    & claude -c -p $lenh --permission-mode auto 2>&1 | Select-Object -Last 5 | ForEach-Object { Ghi "  $_" }
    Ghi "xong, ma thoat $LASTEXITCODE"
}
catch {
    Ghi "loi: $($_.Exception.Message)"
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $khoa -Force -ErrorAction SilentlyContinue
}
