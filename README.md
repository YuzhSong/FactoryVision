# Factory Vision

Smart factory video safety monitoring: Vue frontend, Django backend, and a CUDA-enabled FastAPI AIService.

## Local development

Use the repository scripts. They locate the repository root themselves and invoke the required interpreter directly, so no PowerShell virtual environment activation is needed.

| Service | Fixed runtime | Address |
| --- | --- | --- |
| AIService | `ai-service/.venv/Scripts/python.exe` (Python 3.11) | `http://127.0.0.1:9000/health` |
| Backend | `backend/.venv/Scripts/python.exe` | `http://127.0.0.1:8000/api/health/` |
| Frontend | project `node_modules` | `http://127.0.0.1:5173/` |

Before changing Python dependencies, validate the repository environments:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-python-env.ps1
```

Install frontend dependencies once when `frontend/node_modules` does not exist:

```powershell
Push-Location .\frontend
npm.cmd install
Pop-Location
```

For a first-time local Backend database, run migrations once. Do not run this on every start:

```powershell
Push-Location .\backend
..\.venv\Scripts\python.exe manage.py migrate
Pop-Location
```

Start the complete local stack:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-dev.ps1
```

The script starts Backend, AIService, and Frontend in managed background processes. Logs are written under `.codex-runlogs/`; stop only those processes with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop-local-dev.ps1
```

For focused debugging, start individual services in separate terminals:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-ai-service.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

Do not use system Python or Python 3.14 for AIService, and do not rely on `Activate.ps1` from an older terminal session.

## Video processing

AIService starts independently from the web services. After it is healthy, start the processed stream with the configured RTMP addresses:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9000/streams/start -ContentType 'application/json' -Body '{"mode":"detect"}'
```

Default addresses are:

- Input RTMP: `rtmp://81.70.90.222:1935/live/1`
- Processed RTMP: `rtmp://81.70.90.222:1935/live/1_detected`
- Player URL: `https://webrtc.rainycode.cn:8443/live/1_detected.flv`

Check timing and model scheduling at `http://127.0.0.1:9000/streams/status`. The default stream schedule runs person and helmet inference on alternating analysis ticks; in-stream face recognition is disabled unless `includeFaces: true` is supplied.

## Docker Compose

`docker compose up --build` is useful only for a generic containerized development demonstration. It is not the recommended local GPU AIService path: it does not use the repository Python 3.11 environment or the verified CUDA/Torch combination. Use the PowerShell scripts above for local RTX 4050 development.
