@echo off
setlocal

set "ROOT_DIR=%~dp0..\.."
cd /d "%ROOT_DIR%\ai-service"

if not exist ".venv\Scripts\python.exe" (
  echo [FactoryVision] ai-service\.venv\Scripts\python.exe is missing.
  echo Create the AI service virtual environment and install dependencies first.
  exit /b 1
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo [FactoryVision] WARNING: ffmpeg was not found in PATH.
  echo The AI API can still start, but RTMP processed-stream push will fail until ffmpeg is installed.
)

call ".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 9000
