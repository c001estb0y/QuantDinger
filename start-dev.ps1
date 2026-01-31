# QuantDinger Local Development Startup Script
$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "QuantDinger Dev Server"

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   QuantDinger Dev Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check Python
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
$pythonVersion = py --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Python: $pythonVersion" -ForegroundColor Green
}
else {
    Write-Host "  Error: Python not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Node.js
Write-Host "[2/4] Checking Node.js..." -ForegroundColor Yellow
$nodeOk = $false
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green
    $nodeOk = $true
}
else {
    Write-Host "  Warning: Node.js not found" -ForegroundColor Yellow
}

# Check .env
Write-Host "[3/4] Checking .env..." -ForegroundColor Yellow
$envFile = Join-Path $ScriptDir "backend_api_python\.env"
if (Test-Path $envFile) {
    Write-Host "  .env exists" -ForegroundColor Green
}
else {
    Write-Host "  Creating .env..." -ForegroundColor Yellow
    Copy-Item (Join-Path $ScriptDir "backend_api_python\env.example") $envFile
}

# Check node_modules
Write-Host "[4/4] Checking dependencies..." -ForegroundColor Yellow
$nodeModules = Join-Path $ScriptDir "quantdinger_vue\node_modules"
if ($nodeOk -and (Test-Path $nodeModules)) {
    Write-Host "  Frontend dependencies OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host "Starting Backend (Flask)..." -ForegroundColor Green
$backendPath = Join-Path $ScriptDir "backend_api_python"
Start-Process powershell -ArgumentList "-NoExit -Command cd '$backendPath'; py run.py"

Start-Sleep -Seconds 2

# Start Frontend
if ($nodeOk) {
    Write-Host "Starting Frontend (Vue)..." -ForegroundColor Green
    $frontendPath = Join-Path $ScriptDir "quantdinger_vue"
    Start-Process powershell -ArgumentList "-NoExit -Command cd '$frontendPath'; npm run serve"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend:  http://localhost:5000" -ForegroundColor White
Write-Host "  Frontend: http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "  Login: quantdinger / 123456" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to close this window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
