# Smart Factory Vision

智安工厂实时视频分析监测系统第一阶段项目骨架。

## Tech Stack

- Frontend: Vue 3 + Vite + Element Plus + ECharts
- Backend: Django + Django REST Framework
- AI Service: Python placeholder service for OpenCV / YOLO / face recognition integration
- Database: SQLite for local development, MySQL reserved for future deployment
- CI/CD: Jenkins
- Specification: OpenSpec

## Repository Structure

```text
smart-factory-vision/
  README.md
  Jenkinsfile
  docker-compose.yml
  backend/
  frontend/
  ai-service/
  openspec/
  docs/
```

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### AI Service

```bash
cd ai-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Current Stage

- Stage 1 only: project skeleton setup
- No complex business logic
- No hard-coded large mock datasets
- Frontend gets business data from backend APIs only
- AI service reports results to backend APIs only
