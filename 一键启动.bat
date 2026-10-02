@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 936 >nul 2>&1
set "HERE=%~dp0"
set "LOG=%HERE%start.log"

echo ==================================================
echo   国际无畏契约换肤 · 一键启动 (免卡密破解版)
echo ==================================================
echo.

echo [*] 正在定位 crack 目录 ...
set "CRACK="
for %%D in ("%HERE%crack" "%HERE%..\crack" "%HERE%..\..\crack" "%HERE%extract\crack" "%HERE%..\extract\crack" "%HERE%..\..\extract\crack") do if not defined CRACK if exist "%%~fD\_run_serve.bat" set CRACK=%%~fD\
if not defined CRACK for /f "delims=" %%F in ('dir /b /s "%HERE%_run_serve.bat" 2^>nul') do if not defined CRACK set CRACK=%%~dpF

echo [*] 正在定位 VS.exe ...
set "VSEXE="
for %%F in ("%HERE%VS.exe" "%HERE%extract\VS.exe" "%HERE%..\extract\VS.exe" "%HERE%..\VS.exe") do if not defined VSEXE if exist "%%~fF" set VSEXE=%%~fF
if not defined VSEXE for /f "delims=" %%F in ('dir /b /s "%HERE%VS.exe" 2^>nul') do if not defined VSEXE set VSEXE=%%~fF

echo [*] 正在检查 Python ...
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

> "%LOG%" echo ==== start %date% %time% ====
>>"%LOG%" echo bat  = %~f0
>>"%LOG%" echo crack= %CRACK%
>>"%LOG%" echo vsexe= %VSEXE%
>>"%LOG%" echo py   = %PY%

if not defined CRACK (
    echo.
    echo [X] 找不到 crack 目录 (缺少 crack\_run_serve.bat^)。
    echo     请把随包发来的 crack 文件夹, 和本 bat 放在同一个目录,
    echo     或放在 VS.exe 所在的目录, 然后重新双击本 bat。
    echo.
    >>"%LOG%" echo [X] crack not found
    pause
    exit /b 1
)
if not exist "%CRACK%v6serve.py" (
    echo.
    echo [X] crack 目录里缺少 v6serve.py, 包不完整, 请重新解压整包 (别只解压一半^)。
    echo.
    >>"%LOG%" echo [X] v6serve.py missing
    pause
    exit /b 3
)
if not defined PY (
    echo.
    echo [X] 没检测到 Python。请先装 Python 3, 安装时勾选 Add python.exe to PATH。
    echo     https://www.python.org/downloads/
    echo     装完重新双击本 bat。
    echo.
    >>"%LOG%" echo [X] python not found
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 2
)

echo.
echo [1/4] 关闭占用 8000 端口的旧前端 ...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do (
    echo   kill PID %%P >> "%LOG%"
    taskkill /F /PID %%P >> "%LOG%" 2>&1
)

echo [2/4] 启动本地前端  http://127.0.0.1:8000/ ...
start "v6serve" /min "%CRACK%_run_serve.bat"

echo [3/4] 启动 VS.exe 后端 (请在弹出的 UAC 窗口点"是") ...
if defined VSEXE (
    start "" "%VSEXE%"
) else (
    echo   [!] 没找到 VS.exe, 请自己手动双击 VS.exe 启动后端。
)

echo [4/4] 等 8 秒后打开破解页面 ...
timeout /t 8 /nobreak >nul
start "" "http://127.0.0.1:8000/"

echo.
echo ==================================================
echo  完成。页面顶部出现红色横幅 "V6 破解版已生效" 即成功。
echo  若提示登录: 账号密码随便填, 点登录。
echo  保持 VS.exe 运行 = 后端在线; 本窗口可直接关闭。
echo ==================================================
pause >nul
exit /b 0
