[CmdletBinding()]
param(
    [string]$PythonExecutable,
    [ValidateRange(1, 65535)][int]$Port = 8766,
    [string]$DataRoot,
    [string]$ConfigPath,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
if (-not $DataRoot) { $DataRoot = Join-Path $PSScriptRoot 'var\web' }
if (-not $ConfigPath) { $ConfigPath = Join-Path $PSScriptRoot 'cau_hinh.toml' }
$kttConfig = [IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $kttConfig -PathType Leaf)) { throw ('Khong tim thay cau hinh: ' + $kttConfig) }
$kttRoot = [IO.Path]::GetFullPath($DataRoot)
$kttUrl = 'http://127.0.0.1:' + $Port
$kttHash = [Security.Cryptography.SHA256]::Create()
try {
    $kttRootId = [BitConverter]::ToString($kttHash.ComputeHash([Text.Encoding]::UTF8.GetBytes($kttRoot.ToLowerInvariant()))).Replace('-', '').ToLowerInvariant()
} finally { $kttHash.Dispose() }

$kttSrc = Join-Path $PSScriptRoot 'src'
$kttExpectedVersion = $null
$kttInit = Join-Path $kttSrc 'kho_tri_thuc\__init__.py'
if (Test-Path -LiteralPath $kttInit -PathType Leaf) {
    $kttVersionLine = Select-String -LiteralPath $kttInit -Pattern '__version__\s*=\s*"([^"]+)"' | Select-Object -First 1
    if ($kttVersionLine) { $kttExpectedVersion = $kttVersionLine.Matches[0].Groups[1].Value }
}

function Get-KttHealth {
    try { Invoke-RestMethod -Uri ($kttUrl + '/api/health') -TimeoutSec 5 -ErrorAction Stop } catch { $null }
}
# CRM-41-01-06: ban DEMO (khong phai kho that) phai co engine trich #6 do chinh central nay so huu.
$kttIsThat = Select-String -LiteralPath $kttConfig -Pattern '^\s*environment\s*=\s*"that"' -Quiet
function Assert-KttOwner($Health) {
    if ($Health.application -ne 'kho-tri-thuc-local' -or $Health.root_id -ne $kttRootId) {
        throw ('Cong ' + $Port + ' dang duoc mot ung dung/kho khac su dung. Dung ung dung cu hoac chon -Port khac.')
    }
}
# A server of this same kho keeps running hidden after the window closes.  When
# the code on disk is newer (new version, or files changed after it started),
# it must be restarted, otherwise the old code keeps answering.
function Test-KttStale($Health) {
    if ($kttExpectedVersion -and $Health.version -ne $kttExpectedVersion) { return $true }
    if ($null -eq $Health.started_at) { return $true }
    # CRM-41-01-06: health cu khong co dinh danh engine, hoac engine DEMO cua central da chet -> khong bao san sang; khoi dong lai DUNG central nay
    if (-not $kttIsThat) {
        if ($null -eq $Health.trich6 -or -not $Health.trich6.quan_ly) { return $true }
        if (-not $Health.trich6.san_sang -and [string]$Health.trich6.ly_do -in @('ENGINE_DA_DUNG', 'KHONG_KET_NOI', 'IMPLEMENTATION_KHAC', 'DA_DUNG')) { return $true }
    }
    $kttStarted = [DateTimeOffset]::FromUnixTimeSeconds([long]$Health.started_at).UtcDateTime
    $kttNewest = Get-ChildItem -LiteralPath $kttSrc -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in @('.py', '.js', '.css', '.html', '.svg') } |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    return ($null -ne $kttNewest -and $kttNewest.LastWriteTimeUtc -gt $kttStarted.AddSeconds(2))
}
function Get-KttListenerId {
    try {
        $kttConn = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($kttConn) { return [int]$kttConn.OwningProcess }
    } catch { }
    try {
        $kttLine = netstat -ano -p tcp | Select-String -Pattern ('^\s*TCP\s+127\.0\.0\.1:' + $Port + '\s+\S+\s+LISTEN\w*\s+(\d+)\s*$') | Select-Object -First 1
        if ($kttLine) { return [int]$kttLine.Matches[0].Groups[1].Value }
    } catch { }
    return $null
}
# Chi dung dung tien trinh cua ung dung nay: PID do /api/health bao phai trung PID dang nghe cong, la python, va dong lenh chay
# kho_tri_thuc.giao_dien.server voi dung --root cua kho nay. Khong khop -> khong dung gi ca (khong gianh cong).
function Test-KttOwnProcess($ProcessId) {
    try { $kttProc = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + [int]$ProcessId) -ErrorAction Stop } catch { return $false }
    if ($null -eq $kttProc -or $kttProc.Name -notlike 'python*') { return $false }
    $kttCmd = [string]$kttProc.CommandLine
    return ($kttCmd -like '*kho_tri_thuc.giao_dien.server*' -and $kttCmd.ToLowerInvariant().Contains($kttRoot.ToLowerInvariant()))
}
function Stop-KttServer($Health) {
    $kttOldId = $null
    if ($Health.pid) { $kttOldId = [int]$Health.pid }
    $kttListener = Get-KttListenerId
    if (-not $kttOldId -or ($kttListener -and $kttListener -ne $kttOldId) -or -not (Test-KttOwnProcess $kttOldId)) {
        throw 'Phan mem phien ban cu van dang chay an nhung khong xac minh duoc dung tien trinh cua kho nay. Khoi dong lai may tinh roi mo lai phan mem.'
    }
    Write-Host ('Dang tat phan mem phien ban cu (tien trinh ' + $kttOldId + ') de nap phien ban moi...')
    Stop-Process -Id $kttOldId -Force
    for ($kttWait = 0; $kttWait -lt 50; $kttWait++) {
        if ($null -eq (Get-KttHealth)) { return }
        Start-Sleep -Milliseconds 200
    }
    throw 'Chua tat duoc phan mem phien ban cu. Khoi dong lai may tinh roi mo lai phan mem.'
}
function Assert-KttVersion($Health) {
    if ($kttExpectedVersion -and $Health.version -ne $kttExpectedVersion) {
        throw ('Phan mem dang chay la phien ban ' + $Health.version + ', khac phien ban tren dia ' + $kttExpectedVersion + '. Khoi dong lai may tinh roi mo lai.')
    }
}

# CRM-41-01-06: dung lai CHI khi PID trong health = PID dang nghe cong va la dung tien trinh central cua kho nay
function Assert-KttListener($Health) {
    $kttL = Get-KttListenerId
    if (-not $Health.pid -or ($kttL -and $kttL -ne [int]$Health.pid) -or -not (Test-KttOwnProcess ([int]$Health.pid))) {
        throw ('Cong ' + $Port + ' tra loi health nhung khong xac minh duoc dung tien trinh cua kho nay. Dung ung dung cu hoac chon -Port khac.')
    }
}
function Wait-KttTrich6 {
    if ($kttIsThat) { return }
    $kttH6 = $null
    for ($kttI = 0; $kttI -lt 150; $kttI++) {
        $kttH = Get-KttHealth
        if ($kttH -and $kttH.trich6) { $kttH6 = $kttH.trich6 }
        if ($kttH6 -and $kttH6.san_sang) { Write-Host ('Engine trich #6 DEMO san sang (instance ' + [string]$kttH6.instance + ').'); return }
        if ($kttH6 -and [string]$kttH6.ly_do -notin @('DANG_KHOI_DONG', 'CHUA_KHOI_DONG')) { break }
        Start-Sleep -Milliseconds 400
    }
    $kttLy = if ($kttH6) { [string]$kttH6.ly_do } else { 'KHONG_CO_HEALTH' }
    Write-Host ('Engine trich #6 DEMO CHUA san sang (' + $kttLy + '); trich ho so se bao chua san sang, cac chuc nang khac van dung duoc.')
}

$kttHealth = Get-KttHealth
if ($null -ne $kttHealth) {
    Assert-KttOwner $kttHealth
    Assert-KttListener $kttHealth
    if (Test-KttStale $kttHealth) {
        Stop-KttServer $kttHealth
        $kttHealth = $null
    }
}
if ($null -eq $kttHealth) {
    New-Item -ItemType Directory -Path $kttRoot -Force | Out-Null
    # Chon runtime: tools\chon_runtime.py (chi thu vien chuan) doc <DataRoot>\crm-demo\runtime.local.json (root cai: python, thu muc phu
    # thuoc, thu muc guard), probe kha nang THUC (3.11+, openpyxl, psycopg, khong isolated, phu thuoc + guard nap duoc) va tra ve
    # python + PYTHONPATH dung CHUNG cho buoc chuan bi CRM va server. -PythonExecutable tuong minh: chi dung dung python do.
    $kttRunner = $PythonExecutable
    if (-not $kttRunner) {
        $kttRtFile = Join-Path $kttRoot 'crm-demo\runtime.local.json'
        try { if (Test-Path -LiteralPath $kttRtFile) { $kttRunner = [string]((Get-Content -LiteralPath $kttRtFile -Raw -Encoding UTF8 | ConvertFrom-Json).python) } } catch { $kttRunner = $null }
    }
    if (-not $kttRunner) {
        $kttBundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        if (Test-Path -LiteralPath $kttBundled) { $kttRunner = $kttBundled } else {
            $kttCommand = Get-Command python -ErrorAction SilentlyContinue
            if ($kttCommand) { $kttRunner = $kttCommand.Source }
        }
    }
    if (-not $kttRunner -or -not (Test-Path -LiteralPath $kttRunner)) { throw 'Khong tim thay Python de mo ung dung (RUNTIME_KHONG_CO_PYTHON).' }
    $kttChonArgs = @('-X', 'utf8', (Join-Path $PSScriptRoot 'tools\chon_runtime.py'), '--root', $kttRoot)
    if ($PythonExecutable) { $kttChonArgs += @('--python', $PythonExecutable) }
    $kttPreviousEap = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $kttRtLine = & $kttRunner @kttChonArgs 2>$null | Select-Object -Last 1
    } finally { $ErrorActionPreference = $kttPreviousEap }
    $kttRt = $null
    try { $kttRt = $kttRtLine | ConvertFrom-Json } catch { }
    if ($null -eq $kttRt -or -not $kttRt.ok_app) {
        $kttMa = if ($kttRt) { [string]$kttRt.ma } else { 'RUNTIME_PROBE_LOI' }
        throw ('Python chua san sang cho ung dung (' + $kttMa + '). Xem ' + (Join-Path $kttRoot 'logs'))
    }
    $PythonExecutable = [string]$kttRt.python
    $kttChildPath = [string]$kttRt.pythonpath
    if (-not $kttRt.crm) { Write-Host ('CRM DEMO chua dung duoc tren Python nay (' + [string]$kttRt.ma + '); cac chuc nang khac van mo.') }
    # Moi truong con dung chung (PYTHONPATH = src;phu thuoc;guard, khong ghi bytecode); khoi phuc moi truong caller sau moi lan spawn.
    function Set-KttChildEnv {
        $kttSaved = @{}
        foreach ($kttK in @('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONUTF8')) { $kttSaved[$kttK] = [Environment]::GetEnvironmentVariable($kttK, 'Process') }
        [Environment]::SetEnvironmentVariable('PYTHONPATH', $kttChildPath, 'Process')
        [Environment]::SetEnvironmentVariable('PYTHONDONTWRITEBYTECODE', '1', 'Process')
        [Environment]::SetEnvironmentVariable('PYTHONUTF8', '1', 'Process')
        return $kttSaved
    }
    function Restore-KttEnv($Saved) {
        foreach ($kttK in $Saved.Keys) { [Environment]::SetEnvironmentVariable($kttK, $Saved[$kttK], 'Process') }  # $null = bo bien, nhu truoc khi spawn
    }
    # CRM DEMO tren PostgreSQL: chi khi cau hinh KHONG phai kho that. Buoc chuan bi doc cau hinh ket noi cuc bo (khong in bi mat),
    # tao/nang cap/seed DB DEMO bang quyen quan tri rieng, kiem login ung dung. Loi khong chan mo phan mem; trang CRM bao ro.
    if (-not $kttIsThat -and $kttRt.crm) {
        $kttPreviousEap = $ErrorActionPreference
        $kttSavedEnv = Set-KttChildEnv
        try {
            $ErrorActionPreference = 'Continue'  # stderr cua python khong duoc lam dung launcher (Windows PowerShell 5.1)
            $kttCrmLine = & $PythonExecutable -X utf8 (Join-Path $PSScriptRoot 'tools\chuan_bi_crm_demo.py') --config $kttConfig --root $kttRoot 2>$null | Select-Object -Last 1
            $kttCrmCode = $LASTEXITCODE
        } finally { Restore-KttEnv $kttSavedEnv; $ErrorActionPreference = $kttPreviousEap }
        $kttCrm = $null
        try { $kttCrm = $kttCrmLine | ConvertFrom-Json } catch { }
        if ($kttCrmCode -eq 0 -and $kttCrm) {
            $kttCum = if ($kttCrm.cum) { [string]$kttCrm.cum.ket_qua } else { '' }
            Write-Host ('CRM DEMO san sang: CSDL ' + $kttCrm.db + ', schema ' + $kttCrm.schema_sau + ', PostgreSQL ' + $kttCum)
        } elseif ($kttCrmCode -eq 2) {
            Write-Host 'CRM DEMO chua duoc cau hinh ket noi PostgreSQL cuc bo; cac chuc nang khac van dung duoc.'
        } else {
            $kttMa = if ($kttCrm) { [string]$kttCrm.ma } else { 'KHONG_RO' }
            $kttTep = if ($kttCrm) { [string]$kttCrm.tep_trang_thai } else { '' }
            Write-Host ('CRM DEMO chua san sang (' + $kttMa + '). Chi tiet da loc: ' + (Join-Path $kttRoot ('crm-demo\' + $kttTep)))
        }
    }
    # Log rieng cho tung lan khoi chay/thu lai (khong ghi de log cu, khong xoa log).
    $kttRun = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss') + '-' + $PID
    $kttLogDir = Join-Path $kttRoot 'logs'
    New-Item -ItemType Directory -Path $kttLogDir -Force | Out-Null
    $kttTry = 0
    $kttArguments = @('-X', 'utf8', '-m', 'kho_tri_thuc.giao_dien.server', '--config', ('"' + $kttConfig + '"'), '--root', ('"' + $kttRoot + '"'), '--port', $Port, '--no-browser')
    # Right after an old server was stopped, the port can stay busy for a few
    # seconds; retry while the log says so.
    $kttDeadline = (Get-Date).AddSeconds(90)
    $kttWaitNoted = $false
    while ($true) {
        $kttTry++
        $kttOut = Join-Path $kttLogDir ('server-out-' + $kttRun + '-' + $kttTry + '.log')
        $kttErr = Join-Path $kttLogDir ('server-error-' + $kttRun + '-' + $kttTry + '.log')
        $kttSavedEnv = Set-KttChildEnv  # cung python + PYTHONPATH (src;phu thuoc;guard) nhu buoc chuan bi CRM
        try {
            $kttProcess = Start-Process -FilePath $PythonExecutable -ArgumentList $kttArguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $kttOut -RedirectStandardError $kttErr -PassThru
        } finally { Restore-KttEnv $kttSavedEnv }
        $kttExited = $false
        for ($kttAttempt = 0; $kttAttempt -lt 60; $kttAttempt++) {
            $kttHealth = Get-KttHealth
            if ($null -ne $kttHealth) { break }
            $kttProcess.Refresh()
            if ($kttProcess.HasExited) { $kttExited = $true; break }
            Start-Sleep -Milliseconds 200
        }
        if (-not $kttExited) { break }
        $kttLog = ''
        try { $kttLog = [IO.File]::ReadAllText($kttErr) } catch { }
        if ($kttLog -match '10048|Errno 98|Address already in use' -and (Get-Date) -lt $kttDeadline) {
            if (-not $kttWaitNoted) { Write-Host 'Dang cho cong duoc giai phong (toi da 90 giay)...'; $kttWaitNoted = $true }
            Start-Sleep -Seconds 2
            continue
        }
        throw ('Khong mo duoc ung dung. Xem log: ' + $kttErr)
    }
    if ($null -eq $kttHealth) { throw ('Chua ket noi duoc ung dung. Xem log: ' + $kttErr) }
    Assert-KttOwner $kttHealth
    Assert-KttListener $kttHealth
}
Assert-KttVersion $kttHealth
Wait-KttTrich6
Write-Output ('Kho tri thuc: ' + $kttUrl)
Write-Output ('Thu muc du lieu: ' + $kttRoot)
Write-Output ('Cau hinh: ' + $kttConfig)
if (-not $NoBrowser) { Start-Process $kttUrl }
