# Backend

Django + Django REST Framework backend skeleton for Smart Factory Vision.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Current Scope

- Project skeleton and app boundaries
- Health check endpoint: `/api/health/`
- Swagger / OpenAPI scaffold: `/api/docs/`
- Unified response helper for future APIs
