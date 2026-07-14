# Factory Vision AIService

FastAPI AI 视频处理服务，负责 RTMP 拉流、人员/人脸/安全帽/摔倒/区域检测、持续标注、事件证据生成，并通过 FFmpeg 将带框流回推到 SRS。

## 运行环境

AIService 必须使用 `ai-service/.venv/Scripts/python.exe`（Python 3.11）。不要使用系统 Python、Python 3.14 或其他虚拟环境。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-python-env.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-ai-service.ps1
```

默认读取 `ai-service/.env.local`。服务默认不开启 Uvicorn reload，避免遗留父子进程；只有明确需要热重载时才设置 `AI_SERVICE_DEBUG=true`。

## 接口与视频流

- 健康检查：`http://127.0.0.1:9000/health`
- OpenAPI：`http://127.0.0.1:9000/docs`
- 启动/停止：`POST /streams/start`、`POST /streams/stop`
- 状态与性能指标：`GET /streams/status`

服务启动后不会自动处理 RTMP 流。通常由前端经 Backend 摄像头接口下发启动配置。人物检测始终执行；人脸、安全帽、摔倒、区域检测可独立启用。处理链路使用最新帧策略和容量为 1 的输出缓冲，断流后不会持续处理陈旧帧。

测试命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-ai-service.ps1
```

模型、阈值、Backend 和 SRS 地址均由环境变量配置；模型权重与运行期事件媒体不提交仓库。设计细节见 [AI 服务设计](../docs/06-ai-service-design.md)。
