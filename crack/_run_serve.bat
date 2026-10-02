@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PY=py -3
where py >nul 2>&1 || set PY=python
%PY% v6serve.py >> serve.log 2>&1
