# AIService

The local AIService runtime is fixed to `ai-service/.venv/Scripts/python.exe` and must use Python 3.11. Do not use system Python, Python 3.14, or a previously activated virtual environment.

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-python-env.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-ai-service.ps1
```

Health check: `http://127.0.0.1:9000/health`
OpenAPI: `http://127.0.0.1:9000/docs`

The service starts without Uvicorn reload by default, preventing orphaned parent/child server processes. Set `AI_SERVICE_DEBUG=true` only when intentional code reload is required.

The processed RTMP stream is started separately through `POST /streams/start`; inspect `GET /streams/status` for person, helmet, and optional face inference timing. The default stream path alternates person and helmet model inference and keeps face recognition disabled unless the request contains `includeFaces: true`.
