@echo off
chcp 65001 >nul
title QuantDinger Frontend
cd /d "%~dp0quantdinger_vue"
echo ========================================
echo   启动 QuantDinger 前端
echo ========================================
echo.
echo 注意: 需要 Node.js 16+ 版本
echo.
npm run serve
pause
