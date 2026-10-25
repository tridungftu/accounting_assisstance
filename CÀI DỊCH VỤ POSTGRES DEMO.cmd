@echo off
chcp 65001 >nul
rem Cai PostgreSQL DEMO thanh dich vu Windows (Anh chot 25/10/2026). Tu xin quyen quan tri.
net session >nul 2>&1
if errorlevel 1 (
  powershell.exe -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\cai_dich_vu_postgres_demo.ps1"
pause
