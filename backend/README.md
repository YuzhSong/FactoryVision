# Backend

Django + Django REST Framework backend skeleton for Factory Vision.

## Requirements

- Python 3.12+
- Python 3.14 verified locally

## Quick Start

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Endpoints

- Health check: `http://127.0.0.1:8000/api/health/`
- Swagger / OpenAPI: `http://127.0.0.1:8000/api/docs/`

## Notes

- This `requirements.txt` belongs only to the backend directory
- Running `pip install -r requirements.txt` from the repository root will fail because the root directory does not contain that file
