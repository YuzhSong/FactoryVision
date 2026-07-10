@echo off
setlocal

set "ROOT_DIR=%~dp0..\.."
cd /d "%ROOT_DIR%\backend"

if not exist ".venv\Scripts\python.exe" (
  echo [FactoryVision] backend\.venv\Scripts\python.exe is missing.
  echo Create the backend virtual environment and install dependencies first.
  exit /b 1
)

call ".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 exit /b %errorlevel%

call ".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
