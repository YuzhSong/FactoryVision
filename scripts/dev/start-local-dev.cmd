@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

start "FactoryVision Frontend" cmd /k ""%SCRIPT_DIR%start-frontend-dev.cmd""
start "FactoryVision Backend" cmd /k ""%SCRIPT_DIR%start-backend-dev.cmd""
start "FactoryVision AI Service" cmd /k ""%SCRIPT_DIR%start-ai-service-dev.cmd""

echo FactoryVision local services are starting in separate windows.
