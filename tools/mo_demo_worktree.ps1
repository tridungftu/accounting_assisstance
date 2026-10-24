<#
.SYNOPSIS
    Mo ban DEMO cua MOT worktree tren cong rieng, co CRM PostgreSQL (de worker/lead chup man hinh, Anh kiem cong).

.DESCRIPTION
    Chay duoc tu thu muc bat ky:   powershell -NoProfile -ExecutionPolicy Bypass -File <worktree>\tools\mo_demo_worktree.ps1 -Port 8783

    - DataRoot mac dinh <worktree>\var\demo-<Port> (var\ bi .gitignore). KHONG dung var\web, var\web-that, var\plhn-*; cam cong 8766/8767/8768.
    - Chep tu <repo chinh>\var\web\crm-demo\ vao <DataRoot>\crm-demo\ (neu chua co): runtime.local.json, ket-noi.local.json (chep NGUYEN
      TEP, khong doc/in noi dung), cum-pg.local.json (neu repo chinh co; neu khong thi tao tep KHONG bi mat tro dung cluster PostgreSQL da
      cai canh repo chinh - bat buoc vi mac dinh cua ma tinh vi tri cluster theo thu muc CHA cua worktree).
    - MAC DINH (khong co -CsdlRieng) CSDL PostgreSQL DEMO la CSDL DUNG CHUNG voi ban DEMO cua Anh (ten CSDL nam trong ket-noi.local.json,
      khong phu thuoc DataRoot). Migration chi tien, khong ha. Vi vay truoc khi chuan bi CRM, script so chuoi migration cua worktree voi
      chuoi cua ma chinh: khac -> DUNG (exit 2), khong dung vao CSDL.
    - -CsdlRieng <hau to> (KHUYEN DUNG cho worktree, vd -CsdlRieng p8783; -CsdlRieng auto = p<Port>): goi tools\tao_ket_noi_demo_rieng.py
      de ghi <DataRoot>\crm-demo\ket-noi.local.json trong do CHI TEN CSDL doi thanh kho_crm_demo_lt_<hau to> (cung may chu/login/mat khau
      voi CSDL DEMO cua Anh; khong in DSN). Buoc chuan bi CRM (chuan_bi_crm_demo.py) tu CREATE DATABASE neu chua co roi migrate + seed bang
      login quan tri trong DSN -> CSDL cua Anh KHONG bi nang schema hay lan du lieu thu. Bo kiem chuoi migration (khong con dung chung).
      Tep ket-noi.local.json tu chuan bi khac (khong phai ban sao cua repo chinh, khong phai do script nay tao) khong bi ghi de.
      Tep khac tep cua repo chinh trong DataRoot van duoc coi la CSDL rieng (Anh/root tu chuan bi) khi KHONG dung -CsdlRieng.
    - Fixture: buoc chuan bi CRM doc tests\fixtures va kiem SHA da pin tren byte cua repo chinh; worktree tao bang git thieu 19 tep
      (.gitignore loai *.xml/*.zip) va bi doi LF/CRLF (core.autocrlf=true). Script dong bo tu repo chinh CHI tep thieu hoac khac nhau
      duy nhat o xuong dong (git van coi sach); tep khac noi dung that giu nguyen va duoc bao.
    - -KhongCrm: mo ung dung nhung KHONG noi CSDL PostgreSQL (trang CRM bao chua cau hinh).

    Ma thoat: 0 = da mo; 1 = loi khoi dong; 2 = dung vi an toan CSDL (khong mo).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateRange(1, 65535)][int]$Port,
    [string]$DataRoot,
    [string]$ConfigPath,
    [ValidatePattern('^(auto|[a-z0-9_]{1,47})$')][string]$CsdlRieng,
    [switch]$KhongCrm
)

$ErrorActionPreference = 'Stop'

$kttWt = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$kttLauncher = Join-Path $kttWt 'start-web.ps1'
if (-not (Test-Path -LiteralPath $kttLauncher -PathType Leaf)) { Write-Host ('Khong thay start-web.ps1 o ' + $kttWt); exit 1 }

# ---- 1. Cong va thu muc du lieu: khong dung gi cua ban Anh / kho that
if ($Port -in 8766, 8767, 8768) { Write-Host ('Cong ' + $Port + ' danh cho ban cua Anh (8766/8767/8768). Chon cong khac, vd 8781-8789.'); exit 1 }
if (-not $DataRoot) { $DataRoot = Join-Path $kttWt ('var\demo-' + $Port) }
if (-not $ConfigPath) { $ConfigPath = Join-Path $kttWt 'cau_hinh.toml' }
$kttRoot = [IO.Path]::GetFullPath($DataRoot).TrimEnd('\')
if ($CsdlRieng -and $KhongCrm) { Write-Host '-CsdlRieng va -KhongCrm loai tru nhau.'; exit 1 }
if ($CsdlRieng -eq 'auto') { $CsdlRieng = 'p' + $Port }
$kttConfig = [IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $kttConfig -PathType Leaf)) { Write-Host ('Khong tim thay cau hinh: ' + $kttConfig); exit 1 }
if (-not (Select-String -LiteralPath $kttConfig -Pattern '^\s*environment\s*=\s*"fixture"' -Quiet)) {
    Write-Host 'Chi mo cau hinh moi truong "fixture" (DEMO). Khong dung cau hinh kho that/kho thu.'; exit 1
}

# Repo chinh (nguoi giu var\web) tim tu tep .git cua worktree: .git -> gitdir -> commondir (khong goi git de tranh loi ma hoa duong dan co dau)
function Get-KttMainRoot([string]$Wt) {
    $dotGit = Join-Path $Wt '.git'
    if (Test-Path -LiteralPath $dotGit -PathType Container) { return $Wt }
    if (-not (Test-Path -LiteralPath $dotGit -PathType Leaf)) { return $null }
    $line = [string](Get-Content -LiteralPath $dotGit -Encoding UTF8 -TotalCount 1)
    if ($line -notmatch '^gitdir:\s*(.+)$') { return $null }
    $gd = $Matches[1].Trim()
    if (-not [IO.Path]::IsPathRooted($gd)) { $gd = Join-Path $Wt $gd }
    $gd = [IO.Path]::GetFullPath($gd)
    $cdFile = Join-Path $gd 'commondir'
    if (-not (Test-Path -LiteralPath $cdFile -PathType Leaf)) { return $null }
    $cd = ([string](Get-Content -LiteralPath $cdFile -Encoding UTF8 -TotalCount 1)).Trim()
    return [IO.Path]::GetFullPath((Split-Path -Parent ([IO.Path]::GetFullPath((Join-Path $gd $cd)))))
}
$kttMain = Get-KttMainRoot $kttWt
if (-not $kttMain) { Write-Host 'Khong xac dinh duoc repo chinh tu tep .git cua worktree nay.'; exit 1 }

function Test-KttDuoi([string]$Path, [string]$Base) {
    $p = $Path.TrimEnd('\') + '\'
    $b = $Base.TrimEnd('\') + '\'
    return $p.StartsWith($b, [StringComparison]::OrdinalIgnoreCase)
}
foreach ($kttBase in @($kttMain, $kttWt)) {
    $kttVar = Join-Path $kttBase 'var'
    foreach ($kttCam in @('web', 'web-that')) {
        if (Test-KttDuoi $kttRoot (Join-Path $kttVar $kttCam)) { Write-Host ('DataRoot khong duoc la/nam trong ' + (Join-Path $kttVar $kttCam)); exit 1 }
    }
    if (Test-KttDuoi $kttRoot $kttVar) {
        $kttDau = ($kttRoot.Substring($kttVar.Length).TrimStart('\') -split '\\')[0]
        if ($kttDau -like 'plhn-*') { Write-Host ('DataRoot khong duoc nam trong ' + (Join-Path $kttVar $kttDau)); exit 1 }
    }
}

# ---- 2. Chuan bi <DataRoot>\crm-demo (chep nguyen tep, khong doc/in noi dung ket-noi.local.json)
$kttCrmDir = Join-Path $kttRoot 'crm-demo'
New-Item -ItemType Directory -Path $kttCrmDir -Force | Out-Null
$kttSrcDir = Join-Path $kttMain 'var\web\crm-demo'
function Get-KttBam([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }

$kttRtDst = Join-Path $kttCrmDir 'runtime.local.json'
$kttRtSrc = Join-Path $kttSrcDir 'runtime.local.json'
if (-not (Test-Path -LiteralPath $kttRtDst -PathType Leaf)) {
    if (Test-Path -LiteralPath $kttRtSrc -PathType Leaf) { Copy-Item -LiteralPath $kttRtSrc -Destination $kttRtDst }
    else { Write-Host ('CANH BAO: khong co ' + $kttRtSrc + ' - Python se khong co psycopg, CRM DEMO khong chay.') }
}

# Python cho cac buoc phu (chi thu vien chuan hoac chuoi migration): python cua runtime.local.json neu co, khong thi python tren PATH
function Get-KttPythonTienIch {
    $kttP = $null
    try { if (Test-Path -LiteralPath $kttRtDst -PathType Leaf) { $kttP = [string]((Get-Content -LiteralPath $kttRtDst -Raw -Encoding UTF8 | ConvertFrom-Json).python) } } catch { $kttP = $null }
    if (-not $kttP -or -not (Test-Path -LiteralPath $kttP -PathType Leaf)) { $kttC = Get-Command python -ErrorAction SilentlyContinue; if ($kttC) { $kttP = $kttC.Source } else { $kttP = $null } }
    return $kttP
}

$kttKnDst = Join-Path $kttCrmDir 'ket-noi.local.json'
$kttKnSrc = Join-Path $kttSrcDir 'ket-noi.local.json'
$kttDungChung = $false      # true = worktree nay se noi CHUNG CSDL voi ban DEMO cua Anh
if ($KhongCrm) {
    # tro tep ket noi sang duong dan khong ton tai (chi trong tien trinh nay + server con) -> CRM_CHUA_CAU_HINH, ung dung van mo
    $env:KTT_CRM_DEMO_KET_NOI = Join-Path $kttCrmDir 'khong-noi-csdl.json'
    Write-Host 'Che do -KhongCrm: khong noi CSDL PostgreSQL.'
} elseif ($CsdlRieng) {
    # CSDL RIENG: tep ket noi trong DataRoot = tep nguon doi DUY NHAT ten CSDL (kho_crm_demo_lt_<hau to>); khong in DSN
    $kttPyRieng = Get-KttPythonTienIch
    if (-not $kttPyRieng) { Write-Host 'Khong tim thay Python de tao tep ket noi CSDL rieng.'; exit 1 }
    $kttRiengArgs = @('-I', '-B', '-X', 'utf8', (Join-Path $PSScriptRoot 'tao_ket_noi_demo_rieng.py'), '--hau-to', $CsdlRieng, '--data-root', $kttRoot)
    if (Test-Path -LiteralPath $kttKnSrc -PathType Leaf) { $kttRiengArgs += @('--nguon', $kttKnSrc) }
    $kttPrevEap = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $kttRiengLine = & $kttPyRieng @kttRiengArgs 2>$null | Select-Object -Last 1
        $kttRiengCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $kttPrevEap }
    $kttRieng = $null
    try { $kttRieng = $kttRiengLine | ConvertFrom-Json } catch { }
    if ($kttRiengCode -ne 0 -or -not $kttRieng -or -not $kttRieng.db) {
        $kttLoi = if ($kttRieng -and $kttRieng.loi) { [string]$kttRieng.loi } else { 'khong chay duoc tools\tao_ket_noi_demo_rieng.py' }
        Write-Host ('Khong tao duoc ket noi CSDL rieng: ' + $kttLoi); exit 1
    }
    Write-Host ('CSDL RIENG cho ban DEMO nay: ' + [string]$kttRieng.db + ' (' + [string]$kttRieng.trang_thai + '); CSDL cua Anh khong bi dung vao. Chua co thi buoc chuan bi CRM tu tao.')
    # Bien moi truong KTT_CRM_DEMO_KET_NOI (neu dang dat trong may) se ghi de tep: ep ve DUNG tep vua ghi, chi trong tien trinh nay + server con
    $env:KTT_CRM_DEMO_KET_NOI = $kttKnDst
    # Server cu tren cong nay khoi dong TRUOC khi tep doi co the van noi CSDL cu (vd CSDL dung chung cua Anh): khong tai su dung
    $kttH0 = $null
    try { $kttH0 = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $Port + '/api/health') -TimeoutSec 5 -ErrorAction Stop } catch { $kttH0 = $null }
    if ($null -ne $kttH0) {
        $kttGhi = (Get-Item -LiteralPath $kttKnDst).LastWriteTimeUtc
        $kttBatDau = if ($null -ne $kttH0.started_at) { [DateTimeOffset]::FromUnixTimeSeconds([long]$kttH0.started_at).UtcDateTime } else { [DateTime]::MinValue }
        if ($kttBatDau -lt $kttGhi) {
            Write-Host ('DUNG: server dang chay tren cong ' + $Port + ' (pid ' + $kttH0.pid + ') khoi dong TRUOC khi tep ket noi CSDL rieng duoc ghi, co the van noi CSDL cu.')
            Write-Host ('  Dung no:  Stop-Process -Id ' + $kttH0.pid + '   roi chay lai lenh nay.')
            exit 2
        }
    }
} else {
    if (Test-Path -LiteralPath $kttKnDst -PathType Leaf) {
        $kttDungChung = -not ((Test-Path -LiteralPath $kttKnSrc -PathType Leaf) -and ((Get-KttBam $kttKnDst) -ne (Get-KttBam $kttKnSrc)))
        if (-not $kttDungChung) { Write-Host 'ket-noi.local.json trong DataRoot khac tep cua repo chinh: coi la CSDL RIENG do Anh/root chuan bi.' }
    } elseif (Test-Path -LiteralPath $kttKnSrc -PathType Leaf) {
        Copy-Item -LiteralPath $kttKnSrc -Destination $kttKnDst
        $kttDungChung = $true
    } else {
        Write-Host ('CANH BAO: khong co ' + $kttKnSrc + ' - CRM DEMO se bao chua cau hinh.')
    }
}
# Bien moi truong ghi de tep ket noi (DSN) -> server co the noi CSDL khac voi tep da kiem: bo trong tien trinh nay
$env:KHO_PG_DSN_CRM_DEMO = $null
$env:KHO_PG_DSN_CRM_DEMO_ADMIN = $null

# Vi tri cluster PostgreSQL: ma tinh theo THU MUC CHA cua thu muc chua ma; worktree nam sau .claude\worktrees\ nen phai chi ro cho cluster canh repo chinh
$kttCumDst = Join-Path $kttCrmDir 'cum-pg.local.json'
if (($kttWt -ne $kttMain) -and -not $KhongCrm -and -not (Test-Path -LiteralPath $kttCumDst -PathType Leaf)) {
    $kttCumSrc = Join-Path $kttSrcDir 'cum-pg.local.json'
    if (Test-Path -LiteralPath $kttCumSrc -PathType Leaf) { Copy-Item -LiteralPath $kttCumSrc -Destination $kttCumDst }
    else {
        $kttCha = Split-Path -Parent $kttMain
        $kttPgCtl = Join-Path $kttCha 'var\postgresql16-16.15-runtime\bin\pg_ctl.exe'
        $kttPgData = Join-Path $kttCha 'var\postgresql-ktt-16\data'
        if ((Test-Path -LiteralPath $kttPgCtl -PathType Leaf) -and (Test-Path -LiteralPath $kttPgData -PathType Container)) {
            $kttJson = ([ordered]@{ phien_ban = 1; pg_ctl = $kttPgCtl; data_dir = $kttPgData; pg_version = '16'; host = '127.0.0.1'; port = 5432 } | ConvertTo-Json -Compress)
            [IO.File]::WriteAllText($kttCumDst, $kttJson, (New-Object Text.UTF8Encoding($false)))
        } else {
            Write-Host ('CANH BAO: khong thay cluster PostgreSQL canh repo chinh (' + $kttCha + '\var\postgresql-ktt-16) - CRM DEMO se bao loi cluster.')
        }
    }
}

# ---- 3. Chot an toan CSDL dung chung: chuoi migration cua worktree phai TRUNG chuoi cua ma chinh (ma dang chay ban DEMO cua Anh)
$kttPyChuoi = @'
import sys, json, hashlib
try:
    sys.path.insert(0, sys.argv[1])
    from kho_tri_thuc.ha_tang import pg_migrations as m
    cs = [hashlib.sha256("\n".join(s).encode()).hexdigest() for s in m.PG_MIGRATIONS]
    out = {"ok": True, "v": len(cs), "cs": cs}
except Exception as e:
    out = {"ok": False, "loi": type(e).__name__ + ": " + str(e)[:160]}
print(json.dumps(out))
'@
function Get-KttChuoi([string]$Python, [string]$Src) {
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $out = $kttPyChuoi | & $Python -I -B - $Src 2>$null | Select-Object -Last 1
    } finally { $ErrorActionPreference = $prev }
    try { return ($out | ConvertFrom-Json) } catch { return [pscustomobject]@{ ok = $false; loi = 'khong chay duoc Python de doc chuoi migration' } }
}
$kttLyDo = $null            # ly do dung #1: chuoi migration (chi khi dung chung CSDL)
if ($kttDungChung) {
    $kttPy = Get-KttPythonTienIch
    if (-not $kttPy) { Write-Host 'Khong tim thay Python de kiem chuoi migration.'; exit 1 }
    $kttW = Get-KttChuoi $kttPy (Join-Path $kttWt 'src')
    $kttM = Get-KttChuoi $kttPy (Join-Path $kttMain 'src')
    if (-not $kttW.ok) { $kttLyDo = 'Ma cua worktree nay khong nap duoc chuoi migration PostgreSQL (' + $kttW.loi + '). CRM khong the chay tren ma nay.' }
    elseif (-not $kttM.ok) { $kttLyDo = 'Ma cua repo chinh khong nap duoc chuoi migration (' + $kttM.loi + ') nen khong kiem duoc dong bo voi CSDL cua Anh.' }
    elseif ((($kttW.cs) -join ',') -ne (($kttM.cs) -join ',')) {
        $kttN = [Math]::Min([int]$kttW.v, [int]$kttM.v)
        $kttLech = 0
        for ($kttI = 0; $kttI -lt $kttN; $kttI++) { if ($kttW.cs[$kttI] -ne $kttM.cs[$kttI]) { $kttLech = $kttI + 1; break } }
        if ($kttLech -gt 0) { $kttLyDo = ('Migration so ' + $kttLech + ' cua worktree KHAC repo chinh (khac nhanh): hai ben khong dung chung CSDL duoc (MIGRATION_CHANGED).') }
        elseif ([int]$kttW.v -gt [int]$kttM.v) { $kttLyDo = ('Worktree co THEM migration ' + ([int]$kttM.v + 1) + '..' + $kttW.v + ' so voi repo chinh: mo CRM se NANG CAP CSDL dung chung len ' + $kttW.v + ' va khong ha duoc; ban DEMO cua Anh (' + $kttM.v + ') se het mo duoc CRM.') }
        else { $kttLyDo = ('Worktree THIEU migration ' + ([int]$kttW.v + 1) + '..' + $kttM.v + ' so voi repo chinh: CSDL dung chung co the da len ' + $kttM.v + ' nen CRM bao schema khong khop (FUTURE_SCHEMA). Hop nhat/rebase them tu nhanh tich hop.') }
    }
    if (-not $kttLyDo) {
        Write-Host ('Chuoi migration trung repo chinh (' + $kttW.v + '): dung chung CSDL DEMO voi ban cua Anh la an toan ve schema.')
        Write-Host ('  Luu y: DU LIEU thu o day hien ca o ban DEMO cua Anh; tep dinh kem nam rieng o ' + (Join-Path $kttRoot 'crm-k2') + ' (CSDL tro toi tep ben do).')
    }
}

if ($kttLyDo) {
    Write-Host ''
    Write-Host 'DUNG - khong chuan bi CRM, khong dung vao CSDL:'
    Write-Host ('  ' + $kttLyDo)
    Write-Host '  CSDL PostgreSQL DEMO dung chung voi ban DEMO cua Anh; migration chi tien, khong ha.'
    Write-Host '  Cach xu ly:'
    Write-Host ('   1. Mo khong CRM:   powershell -NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -Port ' + $Port + ' -KhongCrm')
    Write-Host ('   2. CSDL RIENG (khuyen dung):  powershell -NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -Port ' + $Port + ' -CsdlRieng p' + $Port)
    Write-Host '      (tu tao CSDL kho_crm_demo_lt_p<cong> cung may chu/login voi CSDL DEMO; CSDL cua Anh khong doi).'
    Write-Host '   3. Neu chi thieu migration: dua worktree len cung nhanh tich hop voi repo chinh.'
    exit 2
}

# Fixture DEMO (buoc chuan bi CRM doc tests\fixtures, kiem SHA da pin tren byte cua repo chinh). Worktree tao bang git KHONG co du:
# .gitignore loai *.xml/*.zip (19 tep m2_invoice_xml/l11_quantity chi co o repo chinh) va core.autocrlf=true doi LF/CRLF khac byte da pin.
# Dong bo tu repo chinh CHI cac tep thieu hoac khac nhau duy nhat o xuong dong; tep khac noi dung that thi giu nguyen.
if (-not $KhongCrm -and ($kttWt -ne $kttMain)) {
    $kttFxMain = Join-Path $kttMain 'tests\fixtures'
    $kttFxWt = Join-Path $kttWt 'tests\fixtures'
    if (Test-Path -LiteralPath $kttFxMain -PathType Container) {
        $kttThem = 0; $kttSuaEol = 0; $kttGiu = @()
        $kttDuoiVanBan = @('.json', '.xml', '.txt', '.csv', '.md', '.toml')
        foreach ($kttF in (Get-ChildItem -LiteralPath $kttFxMain -Recurse -File)) {
            $kttRel = $kttF.FullName.Substring($kttFxMain.Length).TrimStart('\')
            $kttDst = Join-Path $kttFxWt $kttRel
            if (-not (Test-Path -LiteralPath $kttDst -PathType Leaf)) {
                New-Item -ItemType Directory -Path (Split-Path -Parent $kttDst) -Force | Out-Null
                Copy-Item -LiteralPath $kttF.FullName -Destination $kttDst
                $kttThem++
            } elseif ((Get-KttBam $kttDst) -ne (Get-KttBam $kttF.FullName)) {
                $kttGiong = $false
                if ($kttDuoiVanBan -contains $kttF.Extension.ToLowerInvariant()) {
                    $kttX = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($kttF.FullName)).Replace("`r`n", "`n")
                    $kttY = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($kttDst)).Replace("`r`n", "`n")
                    $kttGiong = ($kttX -ceq $kttY)
                }
                if ($kttGiong) { Copy-Item -LiteralPath $kttF.FullName -Destination $kttDst -Force; $kttSuaEol++ } else { $kttGiu += $kttRel }
            }
        }
        Write-Host ('Fixture DEMO dong bo tu repo chinh: them ' + $kttThem + ' tep thieu, dua ' + $kttSuaEol + ' tep ve dung byte da pin (chi khac xuong dong).')
        if ($kttGiu.Count -gt 0) { Write-Host ('  CANH BAO: ' + $kttGiu.Count + ' tep fixture khac NOI DUNG voi repo chinh, giu nguyen (CRM co the loi FIXTURE_PIN): ' + ($kttGiu -join ', ')) }
    }
}

# ---- 4. Mo bang launcher chuan (chon Python co psycopg, chuan bi CRM, khoi dong server an, doi san sang)
try {
    & $kttLauncher -ConfigPath $kttConfig -DataRoot $kttRoot -Port $Port -NoBrowser
} catch {
    Write-Host ('Khong mo duoc: ' + $_.Exception.Message)
    exit 1
}

# ---- 5. Tu kiem: health + trang thai CRM (token trong trang chu, chi cho tien trinh nay)
$kttBase = 'http://127.0.0.1:' + $Port
try {
    $kttH = Invoke-RestMethod -Uri ($kttBase + '/api/health') -TimeoutSec 10
    Write-Output ('Health: OK, pid ' + $kttH.pid + ', phien ban ' + $kttH.version)
    Write-Output ('Dung server:  Stop-Process -Id ' + $kttH.pid)
    $kttPage = Invoke-WebRequest -Uri ($kttBase + '/') -UseBasicParsing -TimeoutSec 10
    $kttTok = [regex]::Match([string]$kttPage.Content, 'name="ktt-token" content="([^"]+)"').Groups[1].Value
    try {
        $kttCrm = Invoke-RestMethod -Uri ($kttBase + '/api/crm') -Headers @{ 'X-KTT-Token' = $kttTok } -TimeoutSec 30
        Write-Output ('CRM: cau_hinh=' + $kttCrm.cau_hinh)
    } catch {
        $kttMsg = if ($_.ErrorDetails -and $_.ErrorDetails.Message) { [string]$_.ErrorDetails.Message } else { [string]$_.Exception.Message }
        Write-Output ('CRM: CHUA SAN SANG - ' + $kttMsg.Substring(0, [Math]::Min(300, $kttMsg.Length)))
    }
} catch {
    Write-Output ('Tu kiem khong chay duoc: ' + $_.Exception.Message)
}
