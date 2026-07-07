# Deployment

## Local Development

This project contains three services:

- `backend`: Django API service
- `frontend`: Vue + Vite frontend
- `ai-service`: Flask AI placeholder service

Each service installs dependencies independently. Do not expect a shared root-level `requirements.txt`.

### Backend

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### AI Service

```powershell
cd ai-service
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## Verified Local Versions

- Python 3.14.3
- Node.js 24.15.0
- npm 11.12.1

## Environment Variables

### Backend

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DB_ENGINE`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `TIME_ZONE`

Defaults allow local startup with SQLite and no extra configuration.

### AI Service

- `AI_SERVICE_HOST`
- `AI_SERVICE_PORT`
- `AI_SERVICE_DEBUG`
- `BACKEND_API_BASE_URL`

Defaults allow local startup with no extra configuration.

### Frontend

No mandatory environment variables are currently required for local startup.

## CI/CD

Current CI/CD is scaffolded by `Jenkinsfile` and the repository structure only. The local startup flow above is the authoritative way to run the project during the current skeleton stage.
