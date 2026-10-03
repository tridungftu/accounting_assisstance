@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-web.ps1" -ConfigPath "%~dp0cau_hinh.toml" -DataRoot "%~dp0var\web" %*
if errorlevel 1 pause
