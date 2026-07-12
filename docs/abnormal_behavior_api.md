# 异常行为识别接口设计文档

## 1. 文档说明

本文档用于说明智安工厂实时视频分析监测系统中“异常行为识别模块”的接口设计。异常行为识别模块属于算法服务的一部分，主要负责对实时视频流或视频帧进行分析，识别工厂现场的安全风险和异常行为，并将识别结果上报给后端事件中心。

本模块当前重点覆盖以下能力：

- 人员摔倒检测
- 固定警戒区域入侵检测
- 接近危险区域检测
- 未佩戴安全头盔检测
- 人员长时间滞留检测
- 人员离开 / 返回检测
- 异常跑动检测，可作为扩展能力

## 2. 模块边界

### 2.1 算法模块职责

异常行为识别模块负责：

1. 接收摄像头编号、视频流地址和检测规则配置。
2. 启动或停止指定摄像头的异常行为检测任务。
3. 对视频帧进行人员检测、头盔检测、警戒区域判断、摔倒判断等处理。
4. 在检测到异常行为时生成结构化事件。
5. 保存或返回异常截图路径。
6. 将异常事件上报给后端事件中心。

### 2.2 后端服务职责

后端服务负责：

1. 管理摄像头信息、视频流地址和检测规则。
2. 调用算法服务启动或停止检测任务。
3. 接收算法服务上报的异常事件。
4. 将事件保存到事件日志、告警中心和监控日志中。
5. 向前端提供事件查询、告警处理和统计分析接口。

### 2.3 推荐对接方式

课程项目阶段推荐使用：

```text
Django 后端服务 + FastAPI 算法服务 + HTTP API 调用
```

后端向算法服务传入 `camera_id`、`stream_url`、检测类型和规则配置。算法服务独立处理视频流，并在检测到异常时调用后端事件上报接口。

## 3. 异常事件类型定义

| 事件名称 | 事件编码 | 事件级别 | 说明 |
|---|---|---|---|
| 人员出现 | `person_detected` | `normal` | 检测到人员进入画面 |
| 未佩戴安全头盔 | `no_helmet` | `warning` | 人员未佩戴安全头盔 |
| 长时间未佩戴安全头盔 | `no_helmet_alarm` | `alarm` | 未佩戴安全头盔超过阈值时间 |
| 接近危险区域 | `danger_zone_near` | `warning` | 人员距离危险区域低于安全距离 |
| 危险区域入侵 | `danger_zone_intrusion` | `alarm` | 人员进入机械区、危险设备区等警戒区域 |
| 疑似摔倒 | `fall_suspected` | `warning` | 系统检测到疑似摔倒行为 |
| 确认摔倒 | `fall_detected` | `alarm` | 连续多帧确认人员摔倒 |
| 人员长时间滞留 | `abnormal_stay` | `warning` | 人员在指定区域停留超过阈值 |
| 人员离开 | `person_leave` | `normal` | 已识别人员离开指定监控区域 |
| 人员返回 | `person_return` | `normal` | 已识别人员返回指定监控区域 |
| 离开时间过长 | `leave_timeout` | `warning` | 人员离开超过设定时长 |
| 异常跑动 | `abnormal_running` | `warning` | 人员运动速度超过设定阈值 |

事件级别说明：

| 事件级别 | 含义 | 处理方式 |
|---|---|---|
| `normal` | 普通事件 | 仅记录日志 |
| `warning` | 异常事件 | 进入异常列表，并在监控界面提示 |
| `alarm` | 告警事件 | 进入告警中心，需要人工处理 |

## 4. 通用返回格式

所有接口统一使用如下返回结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | number | 状态码，`200` 表示成功，其他表示失败 |
| `message` | string | 返回提示信息 |
| `data` | object | 业务数据 |

## 5. 接口设计

## 5.1 启动异常行为检测任务接口

### 接口说明

后端调用该接口，通知算法服务启动某一路摄像头的异常行为检测任务。

### 请求方式

```http
POST /api/algorithm/abnormal/start
```

### 请求参数

```json
{
  "camera_id": "CAM_001",
  "camera_name": "一号车间摄像头",
  "stream_url": "rtsp://192.168.1.100/live",
  "detect_types": [
    "fall_detected",
    "danger_zone_intrusion",
    "no_helmet",
    "abnormal_stay"
  ],
  "config": {
    "fall_ratio_threshold": 1.2,
    "fall_confirm_frames": 5,
    "helmet_confidence_threshold": 0.6,
    "stay_duration_threshold": 30,
    "running_speed_threshold": 2.5,
    "danger_zones": [
      {
        "zone_id": "ZONE_001",
        "zone_name": "机械臂危险区",
        "points": [
          [100, 200],
          [500, 200],
          [500, 600],
          [100, 600]
        ],
        "safe_distance": 20,
        "stay_time_threshold": 3
      }
    ]
  }
}
```

### 参数说明

| 参数 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `camera_id` | string | 是 | 摄像头编号 |
| `camera_name` | string | 否 | 摄像头名称 |
| `stream_url` | string | 是 | 视频流地址，支持 RTSP、HTTP、本地摄像头编号等 |
| `detect_types` | array | 是 | 需要启用的检测类型 |
| `config` | object | 否 | 检测规则配置 |
| `fall_ratio_threshold` | number | 否 | 摔倒判断宽高比阈值 |
| `fall_confirm_frames` | number | 否 | 摔倒连续确认帧数 |
| `helmet_confidence_threshold` | number | 否 | 头盔检测置信度阈值 |
| `stay_duration_threshold` | number | 否 | 滞留时长阈值，单位秒 |
| `running_speed_threshold` | number | 否 | 异常跑动速度阈值，单位可根据像素位移或实际标定距离确定 |
| `danger_zones` | array | 否 | 危险区域配置 |

### 返回结果

```json
{
  "code": 200,
  "message": "异常行为检测任务启动成功",
  "data": {
    "task_id": "TASK_20260707_0001",
    "camera_id": "CAM_001",
    "status": "running"
  }
}
```

## 5.2 停止异常行为检测任务接口

### 接口说明

用于停止指定摄像头或指定任务的异常行为检测。

### 请求方式

```http
POST /api/algorithm/abnormal/stop
```

### 请求参数

```json
{
  "task_id": "TASK_20260707_0001",
  "camera_id": "CAM_001"
}
```

### 参数说明

| 参数 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `task_id` | string | 否 | 检测任务编号 |
| `camera_id` | string | 否 | 摄像头编号 |

说明：`task_id` 和 `camera_id` 至少传入一个。

### 返回结果

```json
{
  "code": 200,
  "message": "异常行为检测任务已停止",
  "data": {
    "task_id": "TASK_20260707_0001",
    "camera_id": "CAM_001",
    "status": "stopped"
  }
}
```

## 5.3 单帧异常行为检测接口

### 接口说明

用于对上传的单张视频帧或图片进行异常行为识别，适合测试、截图检测或后端按帧调用算法服务。

### 请求方式

```http
POST /api/algorithm/abnormal/detect-frame
```

### 请求类型

```text
multipart/form-data
```

### 请求参数

| 参数 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `camera_id` | string | 是 | 摄像头编号 |
| `image` | file | 是 | 待检测图片 |
| `detect_types` | string | 否 | 检测类型，多个类型用英文逗号分隔 |
| `config` | string | 否 | JSON 字符串格式的检测规则配置 |

### 返回结果

```json
{
  "code": 200,
  "message": "检测成功",
  "data": {
    "camera_id": "CAM_001",
    "timestamp": "2026-07-07 15:30:20",
    "persons": [
      {
        "track_id": "P_001",
        "person_id": "EMP_001",
        "person_name": "张三",
        "bbox": [120, 80, 300, 420],
        "confidence": 0.92,
        "helmet_status": "no_helmet",
        "fall_status": "normal",
        "zone_status": "safe",
        "stay_status": "normal"
      }
    ],
    "events": [
      {
        "event_type": "no_helmet",
        "event_level": "warning",
        "description": "检测到人员未佩戴安全头盔",
        "bbox": [120, 80, 300, 420],
        "confidence": 0.88
      }
    ]
  }
}
```

## 5.4 异常事件上报接口

### 接口说明

当算法模块检测到异常行为后，调用该接口向后端事件中心上报异常事件。后端接收后，将事件保存到告警中心和监控日志中。

### 请求方式

```http
POST /api/events/abnormal/report
```

### 请求参数

```json
{
  "event_id": "EVT_20260707_0001",
  "event_type": "fall_detected",
  "event_level": "alarm",
  "camera_id": "CAM_001",
  "camera_name": "一号车间摄像头",
  "person_id": "EMP_001",
  "person_name": "张三",
  "track_id": "P_001",
  "timestamp": "2026-07-07 15:30:20",
  "bbox": [120, 80, 300, 420],
  "confidence": 0.91,
  "snapshot_path": "/snapshots/CAM_001/EVT_20260707_0001.jpg",
  "description": "检测到人员疑似摔倒",
  "extra_data": {
    "fall_status": "confirmed",
    "fall_ratio": 1.35,
    "confirm_frames": 6,
    "zone_id": null,
    "zone_name": null
  }
}
```

### 参数说明

| 参数 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `event_id` | string | 是 | 事件编号 |
| `event_type` | string | 是 | 事件类型编码 |
| `event_level` | string | 是 | 事件级别，取值为 `normal`、`warning`、`alarm` |
| `camera_id` | string | 是 | 摄像头编号 |
| `camera_name` | string | 否 | 摄像头名称 |
| `person_id` | string | 否 | 人员编号，未识别时为空 |
| `person_name` | string | 否 | 人员姓名，未识别时可为空或为“未知人员” |
| `track_id` | string | 否 | 目标追踪编号 |
| `timestamp` | string | 是 | 事件发生时间 |
| `bbox` | array | 否 | 异常目标边界框，格式为 `[x1, y1, x2, y2]` |
| `confidence` | number | 否 | 检测置信度 |
| `snapshot_path` | string | 否 | 事件截图路径 |
| `description` | string | 是 | 事件描述 |
| `extra_data` | object | 否 | 扩展信息，用于存储摔倒比例、危险区域编号等 |

### 返回结果

```json
{
  "code": 200,
  "message": "异常事件上报成功",
  "data": {
    "event_id": "EVT_20260707_0001",
    "status": "received"
  }
}
```

## 5.5 查询异常检测任务状态接口

### 接口说明

用于查询指定异常行为检测任务的运行状态。

### 请求方式

```http
GET /api/algorithm/abnormal/task/{task_id}
```

### 路径参数

| 参数 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `task_id` | string | 是 | 检测任务编号 |

### 返回结果

```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "task_id": "TASK_20260707_0001",
    "camera_id": "CAM_001",
    "status": "running",
    "start_time": "2026-07-07 15:20:00",
    "detect_types": [
      "fall_detected",
      "danger_zone_intrusion",
      "no_helmet"
    ],
    "fps": 15,
    "last_event_time": "2026-07-07 15:30:20"
  }
}
```

## 5.6 异常检测规则配置接口

### 接口说明

用于新增或更新指定摄像头的异常行为检测规则，包括危险区域坐标、安全距离、摔倒阈值、头盔检测阈值、滞留时间阈值等。

### 请求方式

```http
POST /api/algorithm/abnormal/config
```

### 请求参数

```json
{
  "camera_id": "CAM_001",
  "fall_config": {
    "enabled": true,
    "ratio_threshold": 1.2,
    "confirm_frames": 5
  },
  "helmet_config": {
    "enabled": true,
    "confidence_threshold": 0.6,
    "alarm_delay_seconds": 3
  },
  "stay_config": {
    "enabled": true,
    "duration_threshold": 30,
    "movement_threshold": 20
  },
  "running_config": {
    "enabled": false,
    "speed_threshold": 2.5,
    "confirm_frames": 5
  },
  "danger_zone_config": {
    "enabled": true,
    "zones": [
      {
        "zone_id": "ZONE_001",
        "zone_name": "机械臂危险区",
        "points": [
          [100, 200],
          [500, 200],
          [500, 600],
          [100, 600]
        ],
        "safe_distance": 20,
        "alarm_delay_seconds": 2
      }
    ]
  }
}
```

### 返回结果

```json
{
  "code": 200,
  "message": "异常检测规则配置保存成功",
  "data": {
    "camera_id": "CAM_001",
    "updated": true
  }
}
```

## 6. 检测结果数据结构

### 6.1 人员检测结果

```json
{
  "track_id": "P_001",
  "person_id": "EMP_001",
  "person_name": "张三",
  "bbox": [120, 80, 300, 420],
  "confidence": 0.92,
  "center_point": [210, 250],
  "bottom_center": [210, 420]
}
```

### 6.2 危险区域配置

```json
{
  "zone_id": "ZONE_001",
  "zone_name": "机械臂危险区",
  "camera_id": "CAM_001",
  "points": [
    [100, 200],
    [500, 200],
    [500, 600],
    [100, 600]
  ],
  "safe_distance": 20,
  "danger_level": 3,
  "enabled": true
}
```

### 6.3 异常事件对象

```json
{
  "event_id": "EVT_20260707_0001",
  "event_type": "danger_zone_intrusion",
  "event_level": "alarm",
  "camera_id": "CAM_001",
  "person_id": "EMP_001",
  "track_id": "P_001",
  "timestamp": "2026-07-07 15:30:20",
  "bbox": [120, 80, 300, 420],
  "confidence": 0.89,
  "snapshot_path": "/snapshots/CAM_001/EVT_20260707_0001.jpg",
  "description": "检测到人员进入机械臂危险区",
  "status": "unhandled",
  "extra_data": {
    "zone_id": "ZONE_001",
    "zone_name": "机械臂危险区",
    "safe_distance": 20,
    "current_distance": 0
  }
}
```

## 7. 异常行为判断规则建议

### 7.1 摔倒检测规则

基础版本可结合人体框宽高比和连续帧确认实现：

```text
person_width = x2 - x1
person_height = y2 - y1
fall_ratio = person_width / person_height

当 fall_ratio > ratio_threshold 且连续 confirm_frames 帧成立时，判定为确认摔倒。
```

后续可扩展为人体姿态关键点检测或专用摔倒识别模型。

### 7.2 危险区域入侵规则

取人员检测框的脚底中心点作为位置点：

```text
bottom_center = ((x1 + x2) / 2, y2)
```

若该点进入危险区域多边形，则生成 `danger_zone_intrusion` 告警事件。若该点距离危险区域边界小于安全距离，则生成 `danger_zone_near` 异常事件。

### 7.3 未佩戴安全头盔规则

对人员头部区域或整个人体区域进行安全帽检测：

```text
若人员区域内未检测到 helmet，且持续超过 alarm_delay_seconds，则生成 no_helmet 或 no_helmet_alarm 事件。
```

### 7.4 长时间滞留规则

记录人员目标的中心点轨迹。若人员在指定区域内移动距离小于阈值，且停留时间超过 `duration_threshold`，则生成 `abnormal_stay` 事件。

### 7.5 离开 / 返回规则

结合人员身份识别和目标追踪结果。当已识别人员在指定摄像头或区域中消失超过阈值时，记录 `person_leave`。当该人员再次出现时，记录 `person_return`，并计算离开时长。若离开时长超过阈值，则生成 `leave_timeout` 异常事件。

### 7.6 异常跑动规则

根据目标追踪结果计算人员中心点在连续帧之间的位移速度。若速度持续超过 `speed_threshold` 且连续帧数超过阈值，则生成 `abnormal_running` 事件。

## 8. 与其他模块的对接关系

| 对接模块 | 对接内容 |
|---|---|
| 实时监控模块 | 返回检测框、人员状态、异常提示，用于前端实时展示 |
| 摄像头管理模块 | 获取摄像头编号、名称、位置和视频流地址 |
| 警戒区域模块 | 获取危险区域坐标、安全距离和启用状态 |
| 人脸识别模块 | 获取人员身份、员工编号和陌生人状态 |
| 告警中心模块 | 接收告警事件，进行确认、处理和关闭 |
| 监控日志模块 | 保存异常事件、截图路径、处理状态和时间 |
| 考勤统计模块 | 接收人员离开 / 返回记录，生成考勤统计 |

## 9. 后续扩展

后续可根据项目进度扩展以下能力：

1. 使用 YOLOv8-Pose 或 MediaPipe Pose 提升摔倒检测准确率。
2. 使用 ByteTrack、DeepSORT 等算法增强多目标跟踪能力。
3. 支持 WebSocket 实时推送异常事件到前端。
4. 支持算法任务运行状态监控和性能统计。
5. 支持不同摄像头绑定不同检测模型和规则配置。
