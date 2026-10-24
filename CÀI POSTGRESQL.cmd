@echo off
rem V13 buoc 2: cai PostgreSQL 16 + tao CSDL kho_tri_thuc + migration. Windows se hoi quyen quan tri mot lan (bam Yes).
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -Verb RunAs -Wait -FilePath 'powershell.exe' -ArgumentList '-NoProfile -ExecutionPolicy Bypass -NoExit -File \"%~dp0tools\cai_postgres.ps1\"'"
if errorlevel 1 pause
