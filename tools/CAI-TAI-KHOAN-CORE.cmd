@echo off
setlocal DisableDelayedExpansion
set "KTT_CORE_SCRIPT=%~dp0tao_tai_khoan_core.ps1"
set "KTT_CORE_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

"%KTT_CORE_PS%" -NoLogo -NoProfile -File "%KTT_CORE_SCRIPT%"
if errorlevel 1 goto Loi
echo.
echo Hien con CAN_LEAD cho bootstrap DPAPI. Ap dung se dung an toan.
choice /C YN /N /M "Anh muon nang quyen de kiem tra dieu kien ap dung? [Y/N]: "
if errorlevel 2 goto Huy
if errorlevel 1 goto ApDung
goto Huy

:ApDung
rem The script path travels as data, never interpolated into PowerShell code.
rem No credentials in arguments/environment; no ExecutionPolicy bypass.
"%KTT_CORE_PS%" -NoLogo -NoProfile -Command "try { $q = [char]34; $a = '-NoLogo -NoProfile -File ' + $q + $env:KTT_CORE_SCRIPT + $q + ' -ApDung'; $p = Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $a -Verb RunAs -WindowStyle Hidden -Wait -PassThru -ErrorAction Stop; exit $p.ExitCode } catch { Write-Host 'Khong nang quyen duoc; chua ap dung.'; exit 1 }"
if errorlevel 1 goto Loi
echo Kiem tra dieu kien hoan tat.
pause
exit /b 0

:Huy
echo Da huy. Khong thay doi gi.
pause
exit /b 0

:Loi
echo CHUA AP DUNG THANH CONG. Can lead xu ly bootstrap DPAPI/quyen quan tri.
echo Khong tu chay lai bang tai khoan quan tri de bo qua dieu kien.
pause
exit /b 1
