# Factory Vision

智安工厂实时视频分析监测系统面向工厂安全生产场景，采用前后端分离、AI 服务独立、视频流服务独立接入的项目结构，目标是形成“视频采集-智能识别-事件生成-告警处置-日志追溯-统计分析”的闭环。

当前阶段已经完成基础框架搭建，后续开发应先对齐 `docs/` 和 `openspec/` 中的设计与规范，再进入具体功能实现。

## 开发前必读

新成员开始开发前，请先阅读 [docs/README.md](docs/README.md)，再按职责阅读对应设计文档。所有需求、接口、数据库、AI 输出格式、页面结构、部署和测试约定都以 `docs/` 下的编号文档为准。

推荐阅读顺序：

1. [项目总览](docs/01-project-overview.md)
2. [需求说明](docs/02-requirements.md)
3. [架构设计](docs/03-architecture-design.md)
4. [开发指南](docs/08-development-guide.md)
5. 根据个人分工阅读 API、数据库、AI、前端、部署或测试文档

功能开发前应先确认对应 OpenSpec 和文档是否已经对齐；如果修改接口、数据库、页面、AI 输出或部署方式，必须同步更新文档。

## 技术栈

- Frontend: Vue 3 + Vite + Element Plus + ECharts
- Backend: Django + Django REST Framework
- AI Service: FastAPI + OpenCV + YOLO + dlib / face_recognition 预留
- Video Stream: MediaMTX 或 Nginx-RTMP
- Database: MySQL，开发阶段可使用 SQLite
- API Docs: Swagger / OpenAPI
- CI/CD: Jenkins
- Spec Management: OpenSpec

## 项目结构

```text
FactoryVision/
  backend/        Django REST API 服务
  frontend/       Vue 前端应用
  ai-service/     AI 检测服务骨架
  docs/           项目文档体系
  openspec/       需求与变更规范
  Jenkinsfile     CI 流水线骨架
  docker-compose.yml
```

## 文档导航

正式文档入口见 [docs/README.md](docs/README.md)。

- [项目总览](docs/01-project-overview.md)
- [需求说明](docs/02-requirements.md)
- [架构设计](docs/03-architecture-design.md)
- [API 设计](docs/04-api-design.md)
- [数据库设计](docs/05-database-design.md)
- [AI 服务设计](docs/06-ai-service-design.md)
- [前端设计](docs/07-frontend-design.md)
- [开发指南](docs/08-development-guide.md)
- [团队分工](docs/09-team-division.md)
- [部署与 CI/CD](docs/10-deployment-cicd.md)
- [测试计划](docs/11-test-plan.md)

## 本地启动

推荐使用 Docker Compose 一键启动：

```powershell
docker compose up --build
```

启动后访问：

- Frontend: `http://127.0.0.1:5173/`
- Backend: `http://127.0.0.1:8000/api/health/`
- Backend Swagger: `http://127.0.0.1:8000/api/docs/`
- AI Service: `http://127.0.0.1:9000/health`
- AI Service Docs: `http://127.0.0.1:9000/docs`

如需分别调试服务，可按下面方式手动启动。后端、前端、AI 服务需要分别进入对应目录安装依赖并启动；仓库根目录没有通用 `requirements.txt`。

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
uvicorn app:app --host 0.0.0.0 --port 9000 --reload
```

## 当前实现状态

- Backend: 已有 Django 项目、Swagger 入口、健康检查接口、JWT 登录接口、各业务模块 placeholder API，以及 AI 结果上报校验 stub。
- Frontend: 已有 Login、Dashboard、Monitor、Alerts、Employees、Cameras、Zones、Attendance 页面骨架和路由。
- AI Service: 已有 FastAPI 健康检查接口、自动接口文档和检测模块 placeholder。
- Database: 当前业务表未实现，开发阶段使用 SQLite，目标部署使用 MySQL。

未实现的业务能力在文档中统一标记为 `planned`。
