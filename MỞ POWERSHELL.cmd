@echo off
rem Mo PowerShell ngay tai thu muc du an (kho that). Nhay dup de mo.
powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%~dp0'; Write-Host ('Dang o thu muc: ' + (Get-Location).Path); Write-Host 'Vi du: .\run-that.ps1 init'"
