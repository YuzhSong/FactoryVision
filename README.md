# Factory Vision（智安工厂）

Factory Vision 是面向工厂安全生产场景的实时视频智能监控系统。项目已经完成主要演示闭环：摄像头/手机推流经 SRS 分发，AIService 执行人员、人脸、安全帽、摔倒和区域检测并输出带框视频，Django 持久化事件与告警，Vue 前端提供实时监控、业务管理、告警处置和 AI 日报。

## 已交付能力

- JWT 登录与用户会话。
- 员工档案、人脸录入与人脸库同步。
- 摄像头管理、启停流处理与区域多边形配置。
- 人物框强制开启；人脸、安全帽、摔倒、区域检测可独立开关并记忆上次选择。
- WebRTC 优先、HTTP-FLV 回退的低延迟带框流播放。
- 事件入库、实时 WebSocket 推送、告警筛选/处置、关键帧与回放片段。
- 首页聚合看板与 AI 监控日报预览、Word 导出。
- Jenkins + Docker Compose 云端部署前后端；AIService 在本地 GPU 环境独立运行。

考勤统计仍保留为扩展模块，不属于本版本验收闭环。

## 系统组成

| 模块 | 技术 | 默认地址 |
| --- | --- | --- |
| Frontend | Vue 3、Vite、Element Plus、ECharts | `http://127.0.0.1:5173/` |
| Backend | Django、DRF、Channels、Daphne | `http://127.0.0.1:8000/` |
| AIService | FastAPI、OpenCV、YOLO、InsightFace、FFmpeg | `http://127.0.0.1:9000/` |
| Video Stream | SRS（RTMP / WebRTC / HTTP-FLV） | 按部署环境配置 |
| Database | SQLite（本地）/ PostgreSQL（生产） | 仅由 Backend 访问 |

数据边界：Frontend 只访问 Backend API 与视频播放地址；AIService 不直接写数据库，只通过 Backend API 读取配置、同步人脸库并上报事件。

## 本地启动

AIService 必须使用仓库内 Python 3.11 环境，Backend 使用各自独立环境。不要依赖已激活的 PowerShell 环境。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-python-env.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-dev.ps1
```

服务日志写入 `.codex-runlogs/`。停止由脚本启动的本地服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop-local-dev.ps1
```

也可以在不同终端单独启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-ai-service.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

首次初始化本地数据库：

```powershell
backend\.venv\Scripts\python.exe backend\manage.py migrate
backend\.venv\Scripts\python.exe backend\manage.py seed_dev_data
```

## 验证入口

| 用途 | 地址 |
| --- | --- |
| Backend 健康检查 | `http://127.0.0.1:8000/api/health/` |
| Backend Swagger | `http://127.0.0.1:8000/api/docs/` |
| AIService 健康检查 | `http://127.0.0.1:9000/health` |
| AIService OpenAPI | `http://127.0.0.1:9000/docs` |
| AIService 流状态 | `http://127.0.0.1:9000/streams/status` |

单纯启动 AIService 不会自动处理视频流；正常使用时由前端通过 Backend 摄像头流控制接口启动，也可直接调用 AIService 的 `POST /streams/start` 调试。

## 测试与构建

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-backend.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\test-ai-service.ps1
npm.cmd --prefix frontend run build
npx.cmd openspec validate --all
```

## 部署

云端由 `Jenkinsfile` 使用 `deploy/docker-compose.prod.yml` 构建并部署 PostgreSQL、Backend 和 Frontend。AIService 因 GPU、模型和本地视频链路要求独立运行，通过环境变量连接云端 Backend 与 SRS。

生产配置、回滚与健康检查见 [生产部署指南](docs/guides/production-deployment.md)；完整部署流程见 [部署与 CI/CD](docs/10-deployment-cicd.md)。根目录 `docker-compose.yml` 仅用于通用开发参考，不是推荐的 GPU AIService 运行方式。

## 文档

- [文档总目录](docs/README.md)
- [项目总览](docs/01-project-overview.md)
- [架构设计](docs/03-architecture-design.md)
- [API 设计](docs/04-api-design.md)
- [AI 服务设计](docs/06-ai-service-design.md)
- [开发指南](docs/08-development-guide.md)
- [OpenSpec 使用指南](docs/guides/openspec.md)

OpenSpec 的 `openspec/specs/` 表示当前基线，已完成变更归档在 `openspec/changes/archive/`，`openspec/changes/` 只保留尚未结束的工作。
