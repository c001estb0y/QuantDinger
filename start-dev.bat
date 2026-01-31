@echo off
chcp 65001 >nul
title QuantDinger Dev Launcher
powershell -ExecutionPolicy Bypass -File "%~dp0start-dev.ps1"
