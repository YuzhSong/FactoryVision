@echo off
setlocal

set "ROOT_DIR=%~dp0..\.."
cd /d "%ROOT_DIR%\frontend"

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo [FactoryVision] npm.cmd was not found in PATH.
  echo Install Node.js or add npm.cmd to PATH, then retry.
  exit /b 1
)

if not exist "node_modules" (
  echo [FactoryVision] frontend\node_modules is missing.
  echo Run "npm install" in the frontend directory first.
  exit /b 1
)

call npm.cmd run dev:local
