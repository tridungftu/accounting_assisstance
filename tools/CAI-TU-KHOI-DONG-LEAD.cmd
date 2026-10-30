@echo off
rem Cai tac vu Windows: 30 phut/lan kiem tra va tu khoi dong lai phien lead (CD-037). Khong can quyen quan tri.
schtasks /Create /SC MINUTE /MO 30 /TN "KTT-Lead-Tu-Khoi-Dong" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0lead_tu_khoi_dong.ps1\"" /F
if errorlevel 1 (echo Cai KHONG thanh cong.) else (echo Da cai tac vu KTT-Lead-Tu-Khoi-Dong, 30 phut/lan.)
pause
