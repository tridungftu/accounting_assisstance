@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-web.ps1" -ConfigPath "%~dp0cau_hinh.thu-T8.toml" -DataRoot "%~dp0var\web-thu-T8" -Port 8767 %*
if errorlevel 1 pause
