# Factory Vision Project

## Overview

Factory Vision 是面向工厂安全生产的实时视频智能监控系统。当前版本已完成单路演示场景的主要业务闭环，项目进入结题和维护阶段。

## Current Scope

已实现能力：

- JWT 认证、员工与三角度人脸管理。
- 摄像头 CRUD、流启停、区域绘制与预览。
- 人员、人脸、安全帽、摔倒和区域检测；人物检测始终开启，其余检测可选。
- RTMP 拉流/回推，WebRTC 优先与 HTTP-FLV 回退播放。
- 正式 Event/Alert 持久化、WebSocket 实时推送、告警处置与媒体证据。
- Dashboard 聚合和 AI 监控日报预览/Word 导出。
- Jenkins + Docker Compose 云端 Backend/Frontend/PostgreSQL 部署。

不属于当前结题范围：完整考勤、跨摄像头追踪和活体防伪。

## Architecture Constraints

- Frontend SHALL only access business data through Backend REST/WebSocket APIs.
- AIService SHALL NOT write the database directly; it SHALL use Backend APIs for configuration, face-library synchronization, event reporting, and media upload.
- SRS SHALL transport media only and SHALL NOT own business state.
- Person detection SHALL remain enabled for processed video; optional detections are controlled per stream start.
- Runtime models, databases, logs, keyframes, and replay clips SHALL NOT be committed.
- Local AIService SHALL use `ai-service/.venv/Scripts/python.exe` with Python 3.11.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | Vue 3, Vue Router, Axios, Element Plus, ECharts, Vite, mpegts.js |
| Backend | Django, DRF, SimpleJWT, Channels, Daphne, drf-spectacular |
| AIService | FastAPI, OpenCV, Ultralytics YOLO, InsightFace, ONNX Runtime, FFmpeg |
| Video | SRS, RTMP, WebRTC, HTTP-FLV |
| Database | SQLite local, PostgreSQL production |
| Delivery | Jenkins, Docker Compose, Nginx |

## OpenSpec Workflow

- `openspec/specs/` is the current behavioral baseline.
- `openspec/changes/` contains only active work.
- Completed changes SHALL be merged into the baseline and archived under `openspec/changes/archive/`.
- Documentation and specs SHALL be updated when implementation behavior changes.
