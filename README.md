# Factory Vision

工厂实时视频分析与安全监测系统。

当前仓库是一个多服务项目，包含前端、后端和 AI 服务三个独立目录。启动时需要分别进入对应目录安装依赖，不能在仓库根目录直接执行一次 `pip install -r requirements.txt`。

## Repository Structure

```text
FactoryVision/
  README.md
  docker-compose.yml
  backend/
    manage.py
    requirements.txt
  frontend/
    package.json
  ai-service/
    app.py
    requirements.txt
  docs/
  openspec/
```

## Prerequisites

- Python 3.14 is verified locally for `backend/` and `ai-service/`
- Python 3.12+ is recommended for `backend/` because it uses Django 6
- Node.js 24 is verified locally for `frontend/`
- npm 11 is verified locally for `frontend/`

## Important Notes

- The repository root does not contain a `requirements.txt`
- `backend/requirements.txt` is only for the Django backend
- `ai-service/requirements.txt` is only for the Flask AI service
- `pip install -r requirements.txt` is not machine-specific
- That command always reads the `requirements.txt` in your current directory
- If a teammate runs it from the repo root, it will fail because no such file exists there

## Quick Start

### 1. Backend

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Backend URLs:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/api/health/`
- Swagger: `http://127.0.0.1:8000/api/docs/`

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

- Vite dev server: `http://127.0.0.1:5173/`

### 3. AI Service

```powershell
cd ai-service
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

AI service URL:

- Health check: `http://127.0.0.1:9000/health`

## Start From Repo Root

If you prefer to stay in the repo root, use explicit relative paths:

```powershell
py -3.14 -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt

py -3.14 -m venv ai-service\.venv
ai-service\.venv\Scripts\python -m pip install -r ai-service\requirements.txt
```

This works because the `-r` path is explicit. It is also a good way to avoid confusion about which `requirements.txt` is being used.

## Verified Locally

The following checks passed locally on July 7, 2026:

- `backend`: `pip install -r requirements.txt`
- `backend`: `python manage.py check`
- `backend`: `python manage.py migrate`
- `frontend`: `npm install`
- `frontend`: `npm run build`
- `ai-service`: `pip install -r requirements.txt`

## Common Problems

### `pip install -r requirements.txt` fails in repo root

Reason: there is no root-level `requirements.txt`.

Fix: run the command inside `backend/` or `ai-service/`, or use an explicit path such as:

```powershell
pip install -r backend\requirements.txt
```

### `Couldn't import Django`

Reason: backend virtual environment is not activated, or backend dependencies were not installed.

Fix:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Python version is too old

Reason: the backend depends on Django 6, which requires a newer Python version.

Fix: use Python 3.12+ and preferably Python 3.14 to match the local verified setup and `docker-compose.yml`.

## Docker Compose

The repository also includes `docker-compose.yml`, which uses:

- `python:3.14-slim` for `backend`
- `python:3.14-slim` for `ai-service`
- `node:24-alpine` for `frontend`

That file is a useful reference for the expected runtime versions even if you run everything locally.
