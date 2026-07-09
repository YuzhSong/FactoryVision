# AI 服务设计

## 当前实现状态

`ai-service` 是独立 FastAPI 服务，默认地址为 `http://127.0.0.1:9000`。

当前 AI 侧已经实现的能力：

- FastAPI 服务、健康检查、依赖检查和自动 Swagger 文档。
- YOLO 人员检测，输出 `PERSON_DETECTION`。
- InsightFace 人脸识别、员工人脸库加载、特征提取和缓存增删。
- RGB 基础活体检测，用于防御静态图片、平面照片伪装。
- 陌生人连续确认告警，输出 `STRANGER_ALERT`。
- 未戴安全帽检测，输出 `HELMET_WARNING`。
- 危险区域进入、低于安全距离、停留 10 秒后告警，输出 `ZONE_WARNING`。
- 跌倒检测，姿态关键点优先，bbox 比例兜底，连续帧确认后输出 `FALL_ALERT`。
- 异常跑动检测，基于 `trackId` 连续帧中心点速度输出 `RUNNING_ALERT`。
- 员工离开/返回状态机，输出 `EMPLOYEE_PRESENCE_EVENT`。
- 持续拉取 RTMP/视频流、抽帧分析、OpenCV 画框、FFmpeg 回推处理后视频流。
- 告警事件关键帧和短视频素材保存，用于后续事件回放接入。

当前仍未完成或不属于 AI 侧的能力：

- 前端多边形危险区域绘制未完成。
- Django 区域保存、下发和真实业务闭环未完成。
- Django 员工人脸录入后调用 AI 提特征、保存特征向量、刷新 AI 缓存的完整链路未完成。
- Django 告警入库、事件表、告警表、处置记录表和告警中心真实接口未完成。
- Vue 告警中心仍未接真实告警接口。
- 视频重放攻击、AI 换脸攻击防御未完成，目前只有基础静态图片/平面伪装防御。
- 结构化实时标注 WebSocket 通道未完成。当前实时画面主要走“AI 回推带框视频流 -> SRS -> Vue 播放”。

## 服务边界

AI 服务负责：

- 从视频源或 SRS 拉取帧。
- 运行检测、识别、活体、防区和异常行为算法。
- 在帧上绘制检测框并回推处理后视频流。
- 生成结构化检测结果。
- 通过后端 API 上报检测结果或读取基础配置。
- 维护运行时缓存，例如员工人脸、摄像头、区域。

AI 服务不负责：

- 不直接写数据库。
- 不实现 SRS 或摄像头推流。
- 不承担 Vue 页面展示和告警颜色判断。
- 不承担告警处置状态机、钉钉通知和逐级上报。

## Swagger 与启动

启动：

```powershell
cd ai-service
.\.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 9000 --reload
```

AI-service Swagger：

```text
http://127.0.0.1:9000/docs
```

AI-service OpenAPI JSON：

```text
http://127.0.0.1:9000/openapi.json
```

## 主要接口

| 接口 | 方法 | 状态 | 说明 |
| --- | --- | --- | --- |
| `/health` | GET | implemented | 服务状态、模型状态、缓存状态 |
| `/dependencies` | GET | implemented | Python 包、CUDA、FFmpeg 依赖检查 |
| `/faces/status` | GET | implemented | 人脸库和人脸模型状态 |
| `/faces/extract` | POST | implemented | 从上传文件、URL、base64 或本地路径提取人脸特征 |
| `/faces/reload` | POST | implemented | 从本地或后端加载人脸库 |
| `/cache/status` | GET | implemented | 运行时缓存状态 |
| `/cache/reload` | POST | implemented | 从后端 bootstrap 或请求体重载缓存 |
| `/cache/employees/upsert` | POST | implemented | 增量新增或替换员工人脸缓存 |
| `/cache/employees/delete` | POST | implemented | 删除员工人脸缓存 |
| `/cache/cameras/reload` | POST | implemented | 重载摄像头缓存 |
| `/cache/zones/reload` | POST | implemented | 重载危险区域缓存 |
| `/detect/person` | POST | implemented | 单图人员检测 |
| `/detect/frame` | POST | implemented | 单帧综合检测，包含人员、人脸、区域和异常结果 |
| `/process/stream` | POST | implemented | 调试用，处理有限帧数并可上报后端 |
| `/streams/start` | POST | implemented | 启动持续拉流、检测、画框、回推任务 |
| `/streams/stop` | POST | implemented | 停止持续流处理 |
| `/streams/status` | GET | implemented | 查询持续流任务状态 |

## 输出结果类型

| type | category | 说明 |
| --- | --- | --- |
| `PERSON_DETECTION` | 无 | 人员检测结果 |
| `FACE_RESULT` | 无 | 人脸识别结果 |
| `STRANGER_ALERT` | `abnormal_behavior` | 陌生人告警 |
| `HELMET_WARNING` | `abnormal_behavior` | 未戴安全帽 |
| `ZONE_WARNING` | `abnormal_behavior` | 危险区域或安全距离告警 |
| `RUNNING_ALERT` | `abnormal_behavior` | 异常跑动 |
| `EMPLOYEE_PRESENCE_EVENT` | `abnormal_behavior` | 员工离开或返回 |
| `FALL_ALERT` | `emergency_event` | 跌倒告警 |
| `FIRE_ALERT` | `emergency_event` | 预留，当前算法未实现 |
| `SMOKE_ALERT` | `emergency_event` | 预留，当前算法未实现 |
| `WATER_LEAK_ALERT` | `emergency_event` | 预留，当前算法未实现 |
| `FLOODING_ALERT` | `emergency_event` | 预留，当前算法未实现 |

说明：

- AI-service 只输出 `category` 这种机器可读分类，不输出前端颜色。
- Vue 告警中心应由 Django 返回的告警数据决定显示样式，例如按 `category` 或 `type` 标黄、标红。

## 关键结果示例

### 人员检测

```json
{
  "type": "PERSON_DETECTION",
  "trackId": "t-1",
  "bbox": {"x1": 100, "y1": 120, "x2": 240, "y2": 420},
  "centerPoint": {"x": 170, "y": 270},
  "footPoint": {"x": 170, "y": 420},
  "confidence": 0.94
}
```

### 人脸识别

```json
{
  "type": "FACE_RESULT",
  "trackId": "t-1",
  "employeeId": 1,
  "employeeNo": "E001",
  "name": "张三",
  "matched": true,
  "similarity": 0.91,
  "scoreMargin": 0.08,
  "sampleCount": 3,
  "livenessPassed": true,
  "faceBox": {"x1": 120, "y1": 130, "x2": 190, "y2": 210}
}
```

活体失败时：

```json
{
  "type": "FACE_RESULT",
  "trackId": "t-2",
  "matched": false,
  "label": "spoof",
  "rejectReason": "liveness_failed",
  "livenessPassed": false
}
```

### 危险区域告警

```json
{
  "type": "ZONE_WARNING",
  "category": "abnormal_behavior",
  "trackId": "t-1",
  "zoneId": 3,
  "zoneName": "危险设备区",
  "inside": true,
  "distance": 0,
  "safeDistance": 20,
  "staySeconds": 10.0,
  "minStaySeconds": 10.0,
  "level": "high"
}
```

### 跌倒告警

```json
{
  "type": "FALL_ALERT",
  "category": "emergency_event",
  "trackId": "t-1",
  "isFall": true,
  "confidence": 0.86,
  "durationFrames": 5,
  "level": "high"
}
```

## 视频流链路

默认演示链路：

```text
手机/摄像头/OBS
  -> SRS 原始流 rtmp://81.70.90.222:1935/live/1
  -> ai-service 拉流、检测、画框
  -> SRS 带框流 rtmp://81.70.90.222:1935/live/1_detected
  -> Vue 播放 webrtc://webrtc.rainycode.cn:8443/live/1_detected
```

`/streams/start` 采用捕获循环和处理循环分离：

- 捕获循环持续读取最新帧，只保留一个 `latest_frame`。
- 处理循环读取最新帧执行检测和画框。
- 如果检测慢于采集，旧帧会被丢弃，避免实时画面延迟持续累积。
- `FRAME_DETECT_INTERVAL` 控制重检测间隔，默认每 5 帧执行一次较重检测。

## 缓存与后端通信

AI-service 当前具备这些 HTTP 能力：

- `BackendClient.list_cameras()` 读取后端摄像头列表。
- `BackendClient.list_face_records()` 读取员工或人脸库数据。
- `BackendClient.list_zones()` 读取区域配置。
- `BackendClient.report_ai_results()` 向 `/api/ai-results/report/` 上报 AI 结果。
- `BackendClient.get_bootstrap()` 从 `/api/ai/bootstrap/` 获取启动预热数据。
- `BackendClient.report_realtime_frame_results()` 向 `/api/realtime/frame-results/` 上报实时帧结果。

但 Django 侧目前多数接口仍是占位或未实现，所以这些能力只代表 AI 侧调用链已准备好，不代表三端闭环已经完成。

## 事件回放素材

`ProcessedStreamService` 已接入 `EventMediaRecorder`：

- 检测到告警类结果时保存关键帧。
- 保留事件前后短片段。
- 使用冷却时间避免同一事件连续保存过多素材。
- 默认目录为 `ai-service/data/event_media`。

限制：

- Django 还没有事件回放表和查询接口。
- Vue 告警详情还没有接入回放播放。

## 活体检测限制

当前活体检测是普通 RGB 摄像头下的基础防御：

- 可以拦截部分静态图片、屏幕翻拍、平面照片伪装。
- 没有完成随机动作挑战。
- 没有完成视频重放攻击检测。
- 没有完成 AI 换脸或 deepfake 检测。

如果导师严格要求“静态图片、视频、AI 换脸”三类都防御，还需要继续补随机动作活体或专用反伪模型。

## 关键配置

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `FACE_LIVENESS_ENABLED` | `True` | 是否启用 RGB 活体检测 |
| `FACE_LIVENESS_THRESHOLD` | `0.55` | 活体通过阈值 |
| `FACE_LIVENESS_MIN_FACE_SIZE` | `48` | 活体检测最小人脸尺寸 |
| `FACE_LIVENESS_MODEL_PATH` | 空 | 可选 ONNX 反伪模型 |
| `FACE_LIVENESS_REQUIRE_FOR_ENROLLMENT` | `False` | 人脸录入时是否强制活体通过 |
| `ZONE_MIN_STAY_SECONDS` | `10` | 危险区域停留多少秒后告警 |
| `ZONE_STATE_TTL_SECONDS` | `30` | 区域状态过期时间 |
| `STRANGER_CONFIRM_FRAMES` | `3` | 陌生人连续确认帧数 |
| `STRANGER_COOLDOWN_SECONDS` | `30` | 陌生人告警冷却时间 |
| `EVENT_MEDIA_ENABLED` | `True` | 是否保存事件回放素材 |
| `EVENT_MEDIA_PRE_SECONDS` | `3` | 事件前缓存秒数 |
| `EVENT_MEDIA_POST_SECONDS` | `3` | 事件后保存秒数 |
| `FRAME_DETECT_INTERVAL` | `5` | 持续流重检测间隔 |

## 验证命令

```powershell
cd ai-service
.\.venv\Scripts\python.exe -m compileall app.py ai_config.py modules tests
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

当前本地验证结果：`56 tests OK`。
