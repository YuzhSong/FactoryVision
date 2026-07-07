# AI Service

FastAPI-based AI service skeleton for stream reading, detection pipeline placeholders, and backend event reporting.

## Requirements

- Python 3.14 verified locally

## Quick Start

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 9000 --reload
```

## Endpoints

- Health check: `http://127.0.0.1:9000/health`
- Swagger UI: `http://127.0.0.1:9000/docs`
- OpenAPI schema: `http://127.0.0.1:9000/openapi.json`

## Notes

- This `requirements.txt` belongs only to the AI service directory
- Running `pip install -r requirements.txt` from the repository root will fail because the root directory does not contain that file
