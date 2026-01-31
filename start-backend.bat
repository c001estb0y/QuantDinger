@echo off
chcp 65001 >nul
title QuantDinger Backend
cd /d "%~dp0backend_api_python"
echo ========================================
echo   启动 QuantDinger 后端 API
echo ========================================
echo.
py run.py
pause
