@echo off
chcp 65001 >nul
title QuantDinger Build and Start

echo ========================================
echo    QuantDinger Build and Start
echo ========================================
echo.

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 检查 Node.js
echo [1/5] Checking Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed!
    pause
    exit /b 1
)
echo       Node.js found.

:: 检查 Python
echo [2/5] Checking Python...
where py >nul 2>&1
if errorlevel 1 (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed!
        pause
        exit /b 1
    )
)
echo       Python found.

:: 进入前端目录
echo [3/5] Installing frontend dependencies...
cd /d "%SCRIPT_DIR%quantdinger_vue"
if not exist "package.json" (
    echo [ERROR] package.json not found in quantdinger_vue folder!
    pause
    exit /b 1
)

:: 安装依赖 (使用 --legacy-peer-deps 解决依赖冲突)
call npm install --legacy-peer-deps
if errorlevel 1 (
    echo [ERROR] npm install failed!
    pause
    exit /b 1
)
echo       Dependencies installed.

:: 构建前端
echo [4/5] Building frontend...
call npm run build
if errorlevel 1 (
    echo [ERROR] npm run build failed!
    pause
    exit /b 1
)
echo       Frontend built successfully.

:: 返回根目录并启动
echo [5/5] Starting development servers...
cd /d "%SCRIPT_DIR%"

echo.
echo ========================================
echo    Build completed! Starting servers...
echo ========================================
echo.

:: 调用原有的启动脚本
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start-dev.ps1"

pause
