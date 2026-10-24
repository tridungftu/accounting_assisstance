@echo off
rem V13: mo kho thu T8 tren PostgreSQL (schema v12_thu_t8). Chay "CHUYEN DU LIEU SANG POSTGRESQL (kho thu).cmd" truoc. Kho that khong doi.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-web.ps1" -ConfigPath "%~dp0cau_hinh.thu-T8-postgres.toml" -DataRoot "%~dp0var\web-thu-T8-postgres" -Port 8768 %*
if errorlevel 1 pause
