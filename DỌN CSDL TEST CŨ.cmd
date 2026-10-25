@echo off
chcp 65001 >nul
rem Don CSDL test cu kho_test_* tren cum PostgreSQL DEMO (Anh chot 25/10/2026). Co hop xac nhan truoc khi xoa.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$r = Get-Content -Raw -Encoding UTF8 -LiteralPath '%~dp0var\web\crm-demo\runtime.local.json' | ConvertFrom-Json; $env:PYTHONPATH = ($r.duong_dan_phu_thuoc -join ';'); & $r.python -X utf8 '%~dp0tools\don_csdl_test_cu.py'"
pause
