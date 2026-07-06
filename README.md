# Factory Vision

工厂实时视频分析监测系统第一阶段项目骨架。

## Project Overview

本项目面向工厂安全生产场景，目标是围绕实时视频流接入、人员检测、人脸识别、陌生人告警、危险区域入侵、头盔检测、摔倒检测、异常跑动、告警中心、监控日志与考勤统计，逐步搭建一个前后端分离、AI 服务独立、便于多人并行开发的监测系统。

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

## Development Stages

- Stage 0：文档与范围固化，补齐 PRD、架构、OpenSpec 和项目说明。
- Stage 1：项目骨架搭建，完成 frontend、backend、ai-service、Jenkins、docs、openspec 基础结构。
- Stage 2：基础管理与数据库，补员工、摄像头、区域、事件等基础模型和 CRUD。
- Stage 3：实时视频流展示，跑通摄像头配置、监控页和视频展示闭环。
- Stage 4：人员检测结果接入与前端叠加显示。
- Stage 5：人脸识别与陌生人告警闭环。
- Stage 6：危险区域绘制与入侵检测。
- Stage 7：告警中心与事件日志完善。
- Stage 8：头盔、摔倒、跑动检测接入。
- Stage 9：考勤统计与离开/返回检测。
- Stage 10：Jenkins、测试与交付文档收尾。

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

## Development Rules

- 前端后续只通过后端 API 获取业务数据，不直连数据库。
- AI 服务后续只通过后端 API 上报检测结果，不直接写数据库。
- 当前阶段只实现项目骨架和可运行入口，不落复杂业务逻辑。
- 需要 mock 时，应放到明确的 mock 文件或模块中，避免散落在业务代码里。
