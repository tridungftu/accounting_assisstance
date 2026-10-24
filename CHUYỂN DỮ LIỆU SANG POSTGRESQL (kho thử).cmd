@echo off
rem V13 buoc 4: chep kho.sqlite that -> ban sao, chuyen sang PostgreSQL (kho thu). Khong dung kho that.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\chuyen_kho_thu.ps1"
if errorlevel 1 pause
