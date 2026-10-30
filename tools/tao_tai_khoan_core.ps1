# G2-33 / CD-033, CD-038 engine 3A. UTF-8 without BOM; compatible with PS 5.1.
# This revision is a preview only. Provisioning is blocked until lead supplies
# a reviewed bootstrap that persists credentials as DPAPI CurrentUser ktt_core.
# Never substitute the elevated installer's identity or machine-wide DPAPI.
[CmdletBinding()]
param(
    [switch]$ApDung,
    [switch]$Json,
    [string]$ThuMucDemo
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-GocDemo {
    param([string]$DuongDan)
    $repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    $goc = [IO.Path]::GetFullPath((Join-Path $repo 'var\core-demo\g2-33'))
    if ([string]::IsNullOrWhiteSpace($DuongDan)) { return $goc }

    # String-only validation BEFORE any filesystem access. No UNC, devices,
    # relative paths, ADS, sibling prefixes, traversal or production targets.
    if ($DuongDan -notmatch '^[A-Za-z]:[\\/]' -or
        $DuongDan.Substring(2) -match '[:*?"<>|]' -or
        $DuongDan -match '(^|[\\/])\.\.?([\\/]|$)') {
        throw 'TU_CHOI_DICH: chi nhan duong dan DEMO tuyet doi cua G2-33.'
    }
    $dich = [IO.Path]::GetFullPath($DuongDan).TrimEnd('\', '/')
    if (-not [string]::Equals($dich, $goc, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'TU_CHOI_DICH: ngoai var\core-demo\g2-33; khong truy cap du lieu that.'
    }
    return $goc
}

function New-QuyenDuKien {
    param([string]$TaiKhoan, [string]$Quyen, [bool]$TruyenXuong = $true)
    [pscustomobject]@{
        TaiKhoan = $TaiKhoan
        Quyen = $Quyen
        TruyenXuong = $TruyenXuong
    }
}

function New-MucAclDuKien {
    param([string]$DuongDan, [object[]]$Quyen)
    [pscustomobject]@{
        DuongDan = $DuongDan
        ChuSoHuu = 'ktt_core'
        KeThua = $false
        ThayTheDacl = $true
        Quyen = @($Quyen)
    }
}

function Get-KeHoachTaiKhoan {
    param([string]$GocDemo)
    $engines = @(
        @{ Ma = 'e_mask'; TaiKhoan = 'ktt_e_mask'; LyDo = 'Mask: bi mat rieng' },
        @{ Ma = 'e_ai'; TaiKhoan = 'ktt_e_ai'; LyDo = 'AI Cloud: bi mat rieng' },
        @{ Ma = 'e_hoa_don'; TaiKhoan = 'ktt_e_hoa_don'; LyDo = 'Tai hoa don: phien Windows rieng' },
        @{ Ma = 'e_ocr'; TaiKhoan = 'ktt_e_ocr'; LyDo = 'ABBYY: tai khoan rieng; quyen/phien cu the can lead' }
    )
    $taiKhoan = @(
        [pscustomobject]@{ Ten = 'ktt_core'; Loai = 'LocalUser'; QuanTri = $false; LyDo = 'Core / DPAPI CurrentUser' },
        [pscustomobject]@{ Ten = 'ktt_module'; Loai = 'LocalUser'; QuanTri = $false; LyDo = 'Module han che' }
    )
    foreach ($engine in $engines) {
        $taiKhoan += [pscustomobject]@{
            Ten = $engine.TaiKhoan; Loai = 'LocalUser'; QuanTri = $false; LyDo = $engine.LyDo
        }
    }

    $core = New-QuyenDuKien 'ktt_core' 'FullControl'
    $diQua = @($core)
    foreach ($tk in $taiKhoan | Where-Object { $_.Ten -ne 'ktt_core' }) {
        $diQua += New-QuyenDuKien $tk.Ten 'Traverse' $false
    }
    $acl = @(
        (New-MucAclDuKien $GocDemo $diQua),
        (New-MucAclDuKien (Join-Path $GocDemo 'bi-mat') @($core)),
        (New-MucAclDuKien (Join-Path $GocDemo 'tep') @($core)),
        (New-MucAclDuKien (Join-Path $GocDemo 'chuong-trinh') $diQua),
        (New-MucAclDuKien (Join-Path $GocDemo 'lam-viec') $diQua),
        (New-MucAclDuKien (Join-Path $GocDemo 'chuong-trinh\module') @(
            $core; (New-QuyenDuKien 'ktt_module' 'ReadAndExecute')
        )),
        (New-MucAclDuKien (Join-Path $GocDemo 'lam-viec\module') @(
            $core; (New-QuyenDuKien 'ktt_module' 'Modify')
        ))
    )
    foreach ($engine in $engines) {
        $acl += New-MucAclDuKien (Join-Path $GocDemo ('chuong-trinh\' + $engine.Ma)) @(
            $core; (New-QuyenDuKien $engine.TaiKhoan 'ReadAndExecute')
        )
        $acl += New-MucAclDuKien (Join-Path $GocDemo ('lam-viec\' + $engine.Ma)) @(
            $core; (New-QuyenDuKien $engine.TaiKhoan 'Modify')
        )
    }
    [pscustomobject]@{
        Lat = 'G2-33'
        MoiTruong = 'DEMO'
        TrangThai = 'CAN_LEAD'
        SanSangApDung = $false
        GocDemo = $GocDemo
        TaiKhoan = $taiKhoan
        Acl = $acl
        MatKhau = 'Sinh ngau nhien chi khi co bootstrap DPAPI CurrentUser ktt_core da kiem chung; khong in/ghi ro.'
        ChayLai = 'Kiem SID/local user/nhom/quyen hien co; khong doi mat khau tai khoan cu; khong noi DACL.'
        CanLead = @(
            'Bootstrap tao tai khoan va luu mat khau DPAPI CurrentUser dung ktt_core, ke ca crash/retry; hien CHUA co.',
            'Truoc khi mo ap: kiem reparse point, SID/nhom/dac quyen, ACL con ton tai va owner; loi thi dung.',
            'Lead thu Windows that: con khong doc ket, giai DPAPI, doc Core memory hay duplicate handle.',
            'Khong ap D:\DU-LIEU-KE-TOAN\bi-mat trong G2; ban do ACL chi ktt_core danh cho ket DEMO.',
            'Phien/quyen ABBYY cu the va tich hop G2-21/23/27 van cho lead.'
        )
    }
}

function New-AclTrongBoNho {
    param([object]$Muc, [hashtable]$BanDoSid)
    # Pure ACL template, NEVER written to disk in this revision. New DACL drops
    # inherited/extra grants instead of accumulating grants on each rerun.
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true, $false)
    $chu = [Security.Principal.SecurityIdentifier]::new($BanDoSid[$Muc.ChuSoHuu])
    $acl.SetOwner($chu)
    foreach ($quyen in $Muc.Quyen) {
        $sid = [Security.Principal.SecurityIdentifier]::new($BanDoSid[$quyen.TaiKhoan])
        $keThua = [Security.AccessControl.InheritanceFlags]::None
        if ($quyen.TruyenXuong) {
            $keThua = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
        }
        $ace = [Security.AccessControl.FileSystemAccessRule]::new(
            $sid, [Security.AccessControl.FileSystemRights]$quyen.Quyen, $keThua,
            [Security.AccessControl.PropagationFlags]::None,
            [Security.AccessControl.AccessControlType]::Allow
        )
        $acl.AddAccessRule($ace)
    }
    return $acl
}

function Test-QuyenQuanTri {
    $danhTinh = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        $vai = [Security.Principal.WindowsPrincipal]::new($danhTinh)
        return $vai.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    finally { $danhTinh.Dispose() }
}

function Assert-SanSangApDung {
    if (-not (Test-QuyenQuanTri)) {
        throw 'CAN_QUYEN_QUAN_TRI: -ApDung can quyen quan tri; chua thay doi gi.'
    }
    # Deliberate unconditional gate: no bypass switch, no partial provisioning.
    throw 'CAN_LEAD: chua co bootstrap DPAPI CurrentUser ktt_core an toan; chua thay doi gi.'
}

$gocDemo = Get-GocDemo $ThuMucDemo
$keHoach = Get-KeHoachTaiKhoan $gocDemo
if ($ApDung) { Assert-SanSangApDung }

if ($Json) {
    $keHoach | ConvertTo-Json -Depth 8
}
else {
    Write-Output 'XEM TRUOC G2-33 - KHONG THAY DOI TAI KHOAN / THU MUC / ACL.'
    Write-Output ('DEMO: ' + $keHoach.GocDemo)
    foreach ($tk in $keHoach.TaiKhoan) {
        Write-Output ('Du kien kiem/tao local user han che: ' + $tk.Ten + ' - ' + $tk.LyDo)
    }
    foreach ($muc in $keHoach.Acl) {
        $moTa = @($muc.Quyen | ForEach-Object {
            $_.TaiKhoan + ':' + $_.Quyen + $(if ($_.TruyenXuong) { ' (OI,CI)' } else { ' (chi thu muc nay)' })
        }) -join '; '
        Write-Output ('ACL du kien, owner ktt_core, tat ke thua, thay DACL: ' + $muc.DuongDan + ' => ' + $moTa)
    }
    Write-Output ('Mat khau: ' + $keHoach.MatKhau)
    foreach ($lyDo in $keHoach.CanLead) { Write-Output ('CAN_LEAD: ' + $lyDo) }
    Write-Output 'CHUA SAN SANG AP DUNG. -ApDung se dung truoc moi thay doi, ke ca khi da nang quyen.'
}
