@echo off
rem V13: dang ky viec hang dem 23:30 (phan chieu kho that -> K2, sao luu kho thu PostgreSQL). Chi chay khi anh dang nhap; khong can quyen quan tri.
schtasks /Create /F /SC DAILY /ST 23:30 /TN "KhoTriThuc-DongBoDem" /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%~dp0tools\dong_bo_dem.ps1\""
if errorlevel 1 (echo Khong dang ky duoc lich. & pause & exit /b 1)
echo Da dang ky lich "KhoTriThuc-DongBoDem" luc 23:30 hang ngay. Nhat ky: var\v13\dong-bo-dem.log
echo Chay thu ngay bay gio...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\dong_bo_dem.ps1"
pause
