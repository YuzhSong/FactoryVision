# Factory Vision Backend

Django + DRF + Channels 后端，负责认证、员工与人脸、摄像头、区域、事件、告警、看板、AI 日报以及 AIService 配置/事件上报。

## 启动

Backend 必须直接使用仓库环境 `backend/.venv/Scripts/python.exe`：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

启动脚本执行依赖和 Django 检查后，以 Daphne 启动 `config.asgi:application`，同一端口同时提供 HTTP API 和 WebSocket。

首次初始化或模型迁移后执行：

```powershell
backend\.venv\Scripts\python.exe backend\manage.py migrate
backend\.venv\Scripts\python.exe backend\manage.py seed_dev_data
```

## 验证

- 健康检查：`http://127.0.0.1:8000/api/health/`
- Swagger：`http://127.0.0.1:8000/api/docs/`
- OpenAPI JSON：`http://127.0.0.1:8000/api/schema/`
- 实时事件：`ws://127.0.0.1:8000/ws/realtime/{cameraId}/`

测试命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-backend.ps1
```

本地默认使用 SQLite，生产 Compose 使用 PostgreSQL。详细配置见 [部署与 CI/CD](../docs/10-deployment-cicd.md)。
