# Backend

The local Backend runtime is fixed to `backend/.venv/Scripts/python.exe`. It can use the verified local Python 3.14 environment; it is intentionally separate from AIService Python 3.11.

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

The start script runs `pip check` and `manage.py check`, then starts Django at `http://127.0.0.1:8000/`.

Run migrations only when schema changes require them:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Health check: `http://127.0.0.1:8000/api/health/`
OpenAPI: `http://127.0.0.1:8000/api/docs/`
