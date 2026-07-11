# AI 服务设计

## 当前状态

`ai-service` 当前提供 FastAPI 健康检查接口、自动 OpenAPI 文档、图像检测接口、流检测接口和带框视频流控制接口。人员检测已接入 YOLO，视频帧读取已通过 OpenCV 实现，AI 服务可将检测结果画入画面并通过 FFmpeg 回推到 SRS。人脸识别基础模块已存在，生产人脸库和更多安全行为模型仍按演示需求逐步接入。

## 服务职责

AI 服务负责从视频流中读取帧数据，执行人员检测、人脸识别、头盔检测、危险区域检测、摔倒检测、异常跑动检测，将检测结果画到视频帧上并回推带框视频流，同时将结构化结果通过后端 API 上报。AI 服务不直接写数据库。

## 模块结构

| 模块 | 文件 | 职责 | 当前状态 |
| --- | --- | --- | --- |
| `stream_reader` | `modules/stream_reader.py` | 读取 RTSP/RTMP/HLS 视频流和视频帧 | implemented |
| `person_detector` | `modules/person_detector.py` | 基于 YOLO 检测人员位置，并提供 `PERSON_DETECTION` 结果格式化 | implemented |
| `frame_annotator` | `modules/frame_annotator.py` | 使用 OpenCV 将 bbox、标签和置信度绘制到视频帧 | implemented |
| `stream_writer` | `modules/stream_writer.py` | 使用 FFmpeg 将处理后帧推送为 RTMP 带框视频流 | implemented |
| `processed_stream_service` | `modules/processed_stream_service.py` | 管理后台处理任务，拉原始流、处理帧、回推带框流 | implemented |
| `face_recognition_service` | `modules/face_recognition_service.py` | 加载人脸库并识别人脸身份 | placeholder |
| `helmet_detector` | `modules/helmet_detector.py` | 检测头盔佩戴状态，并提供 `HELMET_WARNING` 结果格式化 | partial implemented |
| `zone_detector` | `modules/zone_detector.py` | 基于人员 footPoint、区域多边形和安全距离判断区域风险 | partial implemented |
| `fall_detector` | `modules/fall_detector.py` | 基于 trackId 连续帧历史、姿态关键点或人体框宽高比判断摔倒风险 | implemented |
| `running_detector` | `modules/running_detector.py` | 基于 trackId 连续帧中心点和时间戳判断异常跑动 | partial implemented |
| `abnormal_behavior_service` | `modules/abnormal_behavior_service.py` | 聚合异常行为检测结果并生成 AI 上报 payload | partial implemented |
| `backend_client` | `modules/backend_client.py` | 读取后端摄像头/员工/区域配置，并将检测结果上报到 `/api/ai-results/report/` | implemented against backend stub |

## 模块输入输出

| 模块 | 输入 | 输出 |
| --- | --- | --- |
| `stream_reader` | 摄像头流地址、重连参数 | 视频帧、帧 ID、时间戳 |
| `processed_stream_service` | 原始 RTMP 地址、输出 RTMP 地址、处理模式 | 带框视频流、任务状态 |
| `person_detector` | 单帧图片 | 人员 bbox、置信度、trackId |
| `face_recognition_service` | 人脸区域图片、员工人脸库 | employeeId、相似度、识别状态 |
| `helmet_detector` | 单帧图片、人员 bbox | 是否佩戴头盔、置信度 |
| `zone_detector` | 人员 footPoint、区域多边形、安全距离 | 入侵状态、区域 ID、距离 |
| `fall_detector` | trackId 连续帧历史、人体框或姿态 | 摔倒状态、置信度 |
| `running_detector` | trackId 连续帧中心点、时间戳或 `frameIndex + fps` | 异常跑动状态、速度、持续帧数 |
| `abnormal_behavior_service` | 摄像头 ID、帧 ID、人员检测结果、trackId 历史、区域配置 | 符合 `/api/ai-results/report/` 的 AI 上报 payload |
| `backend_client` | 检测结果 JSON、后端 API 地址 | 上报结果、事件 ID、告警 ID |

## 通用检测结果格式

```json
{
  "cameraId": 1,
  "frameId": "frame-0001",
  "timestamp": "2026-07-07T10:00:00+08:00",
  "results": []
}
```

## 人员检测输出

```json
{
  "type": "PERSON_DETECTION",
  "trackId": "t-1",
  "bbox": {
    "x1": 100,
    "y1": 120,
    "x2": 240,
    "y2": 420
  },
  "centerPoint": {
    "x": 170,
    "y": 270
  },
  "footPoint": {
    "x": 170,
    "y": 420
  },
  "confidence": 0.94
}
```

## 人脸识别输出

```json
{
  "type": "FACE_RESULT",
  "trackId": "t-1",
  "employeeId": 1,
  "employeeNo": "E001",
  "name": "张三",
  "matched": true,
  "similarity": 0.91,
  "faceBox": {
    "x1": 120,
    "y1": 130,
    "x2": 190,
    "y2": 210
  }
}
```

陌生人识别输出：

```json
{
  "type": "FACE_RESULT",
  "trackId": "t-2",
  "employeeId": null,
  "matched": false,
  "label": "unknown",
  "similarity": 0.32
}
```

## 头盔检测输出

```json
{
  "type": "HELMET_WARNING",
  "trackId": "t-1",
  "helmetStatus": "no_helmet",
  "confidence": 0.88,
  "level": "medium"
}
```

## 摔倒检测输出

```json
{
  "type": "FALL_ALERT",
  "trackId": "t-1",
  "isFall": true,
  "confidence": 0.86,
  "durationFrames": 5,
  "evidenceType": "pose",
  "evidence": {
    "evidenceType": "pose",
    "fallLikeFrames": 5,
    "totalFrames": 5,
    "latestBodyAngle": 12.5,
    "latestThreshold": 35
  },
  "level": "high"
}
```

摔倒检测已接入 `FrameProcessor -> AbnormalBehaviorService -> FallDetector -> BackendClient` 链路。判断策略为：

1. 优先使用姿态关键点，基于肩部与髋部连线相对水平面的角度识别倒地姿态。
2. 当上游人员检测没有输出姿态关键点时，回退到 bbox 宽高比判断横向倒地形态。
3. 只有同一 `trackId` 在最近 `FALL_CONFIRM_FRAMES` 帧内持续满足倒地特征，才输出 `FALL_ALERT`。
4. 后端收到 `FALL_ALERT` 后会创建 `Event` 和 `Alert`，告警状态默认为 `pending`。

## 异常跑动输出

```json
{
  "type": "RUNNING_ALERT",
  "trackId": "t-1",
  "isRunning": true,
  "pixelSpeed": 42.6,
  "threshold": 30,
  "durationFrames": 6,
  "level": "medium"
}
```

异常跑动不是 YOLO 原生能力。YOLO 只能提供人员检测框，异常跑动需要基于以下信息二次判断：

1. `trackId`: 跨帧跟踪同一人员。
2. 连续帧中心点: 记录 bbox 中心点或 footPoint。
3. 像素速度: 根据点位位移和帧时间差计算，优先使用 ISO 时间字符串或数值时间戳，其次回退到 `frameIndex + fps`。
4. 连续帧阈值: 只有连续多帧超过速度阈值才判定为异常跑动。
5. 场景校准: 不同摄像头视角下速度阈值需要独立配置。

## 危险区域判断输出

```json
{
  "type": "ZONE_WARNING",
  "trackId": "t-1",
  "zoneId": 3,
  "zoneName": "危险设备区",
  "footPoint": {
    "x": 170,
    "y": 420
  },
  "inside": true,
  "distance": 0,
  "safeDistance": 20,
  "level": "high"
}
```

危险区域检测需要前端在画面上绘制多边形区域，并保存区域坐标。AI 服务根据人员 `footPoint` 判断：

1. `footPoint` 是否位于多边形内部。
2. `footPoint` 到区域边界的距离是否低于安全距离。
3. 是否需要结合摄像头透视关系进行阈值校准。

不应只使用 bbox 中心点判断区域入侵，因为人员脚底位置更能代表人员实际站立点。

## AI 上报流程

```mermaid
sequenceDiagram
    participant Stream as 视频流服务
    participant Reader as stream_reader
    participant Detector as 检测模块
    participant Client as backend_client
    participant Backend as Backend API

    Reader->>Stream: 拉取视频帧
    Reader-->>Detector: frame, frameId, timestamp
    Detector->>Detector: 人员、人脸、头盔、区域、摔倒、跑动检测
    Detector-->>Client: 检测结果 JSON
    Client->>Backend: POST /api/ai-results/report/
    Backend-->>Client: eventIds, alertIds
```

## 人脸编码提取接口

Django 后端在员工人脸录入时调用此接口，获取 128 维人脸特征编码。

调用方：**Django Backend**

### 接口定义

| 项 | 内容 |
| --- | --- |
| 接口说明 | 提取单张图片的人脸编码 |
| URL | `/faces/extract` |
| Method | `POST` |
| 状态 | planned |

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `imageBase64` | string | 是 | 人脸图片 base64，支持 data URL 前缀 |

请求示例：

```json
{
  "imageBase64": "data:image/jpeg;base64,/9j/4AAQ..."
}
```

### 响应

成功（检测到合格人脸）：

```json
{
  "code": 200,
  "data": {
    "featureVector": [0.12, -0.34, 0.56, "..."]
  }
}
```

失败——未检测到人脸：

```json
{
  "code": 422,
  "message": "未检测到人脸",
  "data": null
}
```

失败——图片质量不足（det_score 低于阈值）：

```json
{
  "code": 422,
  "message": "图片质量不足",
  "data": null
}
```

失败——图片无法解码：

```json
{
  "code": 400,
  "message": "无法解码图片",
  "data": null
}
```

### 处理流程

```
Django 传入 imageBase64
    │
    ├── _load_image → 自动识别 base64 → 解码为 BGR 帧
    │
    ├── _detect_faces → InsightFace 检测
    │       │
    │       ├── 0 个人脸 → HTTP 422 "未检测到人脸"
    │       │
    │       └── 检测到人脸 → 获取 det_score
    │               │
    │               ├── det_score < 阈值 → HTTP 422 "图片质量不足"
    │               │
    │               └── det_score >= 阈值 → _face_embedding()
    │                       │
    │                       └── HTTP 200 {featureVector: [归一化 128 维向量]}
    │
    └── cv2.imdecode 失败 → HTTP 400 "无法解码图片"
```

### 设计约束

1. 质量阈值由 AI Service 内部控制，不对外暴露。
2. AI Service 不存储图片和编码，处理完即丢弃。
3. 此接口仅供 Django 后端内部调用，前端不直接访问。

## 带框视频流流程

```mermaid
sequenceDiagram
    participant Source as 手机 / 摄像头 / OBS
    participant SRS as SRS 视频流服务
    participant AI as AI Service
    participant FE as Frontend

    Source->>SRS: RTMP 推送 /live/1
    AI->>SRS: RTMP 拉取 /live/1
    AI->>AI: YOLO / 人脸 / 安全行为检测
    AI->>AI: OpenCV 绘制检测框
    AI->>SRS: FFmpeg 回推 /live/1_detected
    FE->>SRS: WebRTC 播放 /live/1_detected
```

默认演示地址：

| 类型 | 地址 |
| --- | --- |
| 原始输入流 | `rtmp://81.70.90.222:1935/live/1` |
| AI 输出流 | `rtmp://81.70.90.222:1935/live/1_detected` |
| 前端播放流 | `webrtc://webrtc.rainycode.cn:8443/live/1_detected` |

流处理控制接口由 AI Service 暴露：`POST /streams/start`、`POST /streams/stop`、`GET /streams/status`。`mode=test` 用于画测试框验证链路，`mode=detect` 用于真实检测。

## 异常处理

| 场景 | 处理方式 |
| --- | --- |
| 视频流断开 | 重连并上报摄像头离线状态 |
| 模型加载失败 | 服务启动失败或降级为不可用状态 |
| FFmpeg 不可用 | `/dependencies` 标记 ffmpeg 缺失，带框流任务启动失败 |
| 后端上报失败 | 重试并记录本地错误日志 |
| 检测结果格式错误 | 丢弃异常结果并记录 frameId |
| 摄像头未配置区域 | 跳过区域检测 |
