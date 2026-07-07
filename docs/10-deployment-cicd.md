# 部署与 CI/CD

## 当前状态

当前项目处于基础框架阶段。`docker-compose.yml` 已提供三个服务的容器启动参考，`Jenkinsfile` 已包含 Checkout、Backend Check、Frontend Build、AI Service Check 阶段。业务服务部署、视频流服务和制品归档仍为 `planned`。

## 本地启动方式

### 后端

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

访问地址：

- `http://127.0.0.1:8000/api/health/`
- `http://127.0.0.1:8000/api/docs/`

### 前端

```powershell
cd frontend
npm install
npm run dev
```

访问地址：

- `http://127.0.0.1:5173/`

### AI 服务

```powershell
cd ai-service
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 9000 --reload
```

访问地址：

- `http://127.0.0.1:9000/health`
- `http://127.0.0.1:9000/docs`

## 数据库初始化

开发阶段默认使用 SQLite。

```powershell
cd backend
python manage.py migrate
```

目标部署使用 MySQL 时，需要配置后端环境变量：

| 变量 | 说明 |
| --- | --- |
| `DB_ENGINE` | Django 数据库引擎 |
| `DB_NAME` | 数据库名 |
| `DB_USER` | 数据库用户 |
| `DB_PASSWORD` | 数据库密码 |
| `DB_HOST` | 数据库地址 |
| `DB_PORT` | 数据库端口 |

业务表当前为 `planned`，后续实现模型后需要提交 migration。

## SRS 视频流服务

视频流服务用于接入摄像头、手机或 OBS 的 RTMP 原始流，并向前端和 AI 服务分发可消费的视频地址。当前演示环境使用 SRS。

推荐职责：

1. 接入采集端原始 RTMP 流。
2. 转换为前端可播放的 WebRTC 地址。
3. 为 AI 服务保留稳定的 RTMP 拉流地址。
4. 提供摄像头在线状态检查能力。

当前演示流地址：

| 用途 | 地址 |
| --- | --- |
| 手机推原始流 | `rtmp://81.70.90.222:1935/live/1` |
| AI 输出带框流 | `rtmp://81.70.90.222:1935/live/1_detected` |
| 前端播放带框流 | `webrtc://webrtc.rainycode.cn:8443/live/1_detected` |

SRS 云端端口包括 `1935/tcp`、`8443/tcp`、`8000/udp`、`1985/tcp` 和 `8080/tcp`。AI Service 需要可用的 `ffmpeg` 可执行文件以回推带框视频流。

## Docker Compose 参考

当前 `docker-compose.yml` 使用：

| 服务 | 镜像 | 端口 |
| --- | --- | --- |
| backend | `python:3.14-slim` | `8000` |
| frontend | `node:24-alpine` | `5173` |
| ai-service | `python:3.14-slim` | `9000` |

`ai-service` 容器启动时会安装 `ffmpeg`，用于将 AI 处理后的 OpenCV 帧重新编码并推送到 SRS RTMP 输出流。生产部署建议改为自定义镜像，把 `ffmpeg` 固化到镜像层，避免每次启动重复安装。

## Jenkins Pipeline 阶段

```mermaid
flowchart LR
    Checkout["Checkout"] --> Backend["Backend Check"]
    Backend --> Frontend["Frontend Build"]
    Frontend --> AI["AI Service Check"]
    AI --> Archive["Archive Artifacts"]
```

### Checkout

拉取仓库代码，确保工作区为本次构建对应提交。

### Backend Check

当前脚本：

```sh
cd backend
python -m pip install -r requirements.txt
python manage.py check
```

建议后续增加：

```sh
python manage.py test
```

### Frontend Build

当前脚本：

```sh
cd frontend
npm install
npm run build
```

### AI Service Check

当前脚本：

```sh
cd ai-service
python -m pip install -r requirements.txt
python -m compileall .
```

### Archive Artifacts

当前 `Jenkinsfile` 未实现归档阶段，状态为 `planned`。建议归档：

1. 前端 `dist/`。
2. 后端检查日志。
3. AI 服务检查日志。
4. 测试报告。

## 常见问题排查

| 问题 | 原因 | 处理方式 |
| --- | --- | --- |
| 根目录执行 `pip install -r requirements.txt` 失败 | 根目录没有通用 requirements 文件 | 进入 `backend` 或 `ai-service` 目录执行 |
| Django 无法导入 | 未激活虚拟环境或依赖未安装 | 激活 `.venv` 后重新安装依赖 |
| Django 依赖安装失败 | Python 版本过低 | 使用 Python 3.12+，本地验证版本为 3.14 |
| 前端启动失败 | Node 或 npm 版本不匹配 | 使用 Node 24 / npm 11 或兼容版本 |
| AI 服务健康检查失败 | FastAPI 或 uvicorn 依赖未安装，或端口被占用 | 安装依赖并检查 9000 端口 |
| 视频流无法播放 | SRS 未收到原始流或带框流，播放地址不可用 | 检查 SRS 端口、RTMP 推流、AI 回推和 WebRTC 播放地址 |
| Jenkins 构建失败 | 构建机缺少 Python、Node 或网络依赖 | 固定构建环境并缓存依赖 |
