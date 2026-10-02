@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [*] 正在启动本地免卡密 UI (请先确保 VS.exe 已运行, 本地后端 8080 在线) ...
start "" /min cmd /c "set PYTHONIOENCODING=utf-8 && py -3 v6serve.py > serve.log 2>&1"
timeout /t 3 >nul
start "" "http://127.0.0.1:8000/"
echo [*] 已打开 http://127.0.0.1:8000/   (关闭本窗口不影响, 服务在最小化窗口里运行)
