@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "LOG=%~dp0start.log"
set "CRACK=%~dp0..\crack"

echo ==== start %date% %time% ==== > "%LOG%"
echo dp0 = %~dp0 >> "%LOG%"
echo crack = %CRACK% >> "%LOG%"

echo ==========================================
echo   V6Changer one-click start
echo   log: %LOG%
echo ==========================================
echo.

echo [1/3] kill old frontend on port 8000 ...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do (
    echo   kill PID %%P >> "%LOG%"
    taskkill /F /PID %%P >> "%LOG%" 2>&1
)

echo [2/3] start local frontend (127.0.0.1:8000) ...
start "v6serve" /min "%CRACK%\_run_serve.bat"

echo [3/3] start VS.exe backend (approve the UAC prompt) ...
start "" "%~dp0VS.exe"

echo.
echo waiting 8s for backend, then opening crack page ...
timeout /t 8 /nobreak >nul
start "" "http://127.0.0.1:8000/"

echo.
echo DONE. Page should show red banner: V6 crack active.
echo If login is asked: any user/pass works.
echo Keep VS.exe running = backend online.
echo.
echo (this window will stay open; press any key to close)
pause >nul
