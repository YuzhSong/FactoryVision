# API 设计

## 当前实现状态

当前后端已实现：

- `GET /api/health/`: implemented
- `GET /api/users/`: placeholder
- `GET /api/employees/`: placeholder
- `GET /api/cameras/`: placeholder
- `GET /api/zones/`: placeholder
- `GET /api/events/`: placeholder
- `GET /api/attendance/`: placeholder
- `GET /api/ai-results/`: placeholder
- `GET /api/schema/`: implemented
- `GET /api/docs/`: implemented

除上述 placeholder 外，本文档中设计的业务接口均为 `planned`。

## 统一返回格式

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "requestId": "uuid"
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | number | 业务状态码 |
| `message` | string | 返回说明 |
| `data` | object / array / null | 业务数据 |
| `requestId` | string | 请求追踪 ID |

说明：当前 `common.response.api_response` 默认 `code=0`。后续业务接口应统一调整为本文档约定的 `200` 成功码，或在文档中明确兼容策略。

## 错误码规范

| code | HTTP 状态 | 说明 |
| --- | --- | --- |
| 200 | 200 | 成功 |
| 400 | 400 | 请求参数错误 |
| 401 | 401 | 未登录或 token 无效 |
| 403 | 403 | 无权限访问 |
| 404 | 404 | 资源不存在 |
| 409 | 409 | 数据冲突 |
| 422 | 422 | 业务校验失败 |
| 500 | 500 | 服务内部错误 |
| 6001 | 400 | 摄像头不可用 |
| 6002 | 400 | 视频流不可访问 |
| 7001 | 422 | AI 上报格式错误 |
| 7002 | 422 | AI 结果无法匹配摄像头 |
| 8001 | 422 | 告警状态流转非法 |

## 通用分页参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | number | 否 | 页码，默认 1 |
| `pageSize` | number | 否 | 每页数量，默认 20 |
| `keyword` | string | 否 | 关键词 |

分页响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "items": []
  },
  "requestId": "uuid"
}
```

## Health

### 健康检查

| 项 | 内容 |
| --- | --- |
| 接口说明 | 检查后端服务是否可用 |
| URL | `/api/health/` |
| Method | `GET` |
| 状态 | implemented |

请求参数：无。

请求示例：

```http
GET /api/health/
```

响应示例：

```json
{
  "code": 0,
  "message": "Backend service is healthy",
  "data": {
    "service": "backend",
    "status": "ok",
    "stage": "skeleton"
  },
  "requestId": "uuid"
}
```

状态说明：当前代码使用 placeholder 序列化器返回服务状态。

## Auth 用户认证接口

### 登录

| 项 | 内容 |
| --- | --- |
| 接口说明 | 用户登录并获取访问凭证 |
| URL | `/api/auth/login/` |
| Method | `POST` |
| 状态 | planned |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `username` | string | 是 | 登录账号 |
| `password` | string | 是 | 登录密码 |

请求示例：

```json
{
  "username": "admin",
  "password": "password"
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "jwt-token",
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin"
    }
  },
  "requestId": "uuid"
}
```

状态说明：登录成功返回 token，失败返回 `401`。

### 退出登录

| 项 | 内容 |
| --- | --- |
| 接口说明 | 清理当前登录态 |
| URL | `/api/auth/logout/` |
| Method | `POST` |
| 状态 | planned |

请求参数：无。

请求示例：

```json
{}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": null,
  "requestId": "uuid"
}
```

状态说明：前端收到成功响应后清理本地 token。

## Users 用户管理接口

### 用户模块占位接口

| 项 | 内容 |
| --- | --- |
| 接口说明 | 返回用户模块 placeholder 状态 |
| URL | `/api/users/` |
| Method | `GET` |
| 状态 | placeholder |

请求参数：无。

请求示例：

```http
GET /api/users/
```

响应示例：

```json
{
  "code": 0,
  "message": "Users module placeholder",
  "data": {
    "module": "users",
    "status": "placeholder"
  },
  "requestId": "uuid"
}
```

状态说明：当前只用于证明路由存在。

### 用户列表

| 项 | 内容 |
| --- | --- |
| 接口说明 | 查询系统用户列表 |
| URL | `/api/users/list/` |
| Method | `GET` |
| 状态 | planned |

请求参数：通用分页参数。

请求示例：

```http
GET /api/users/list/?page=1&pageSize=20
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "items": [
      {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "isActive": true
      }
    ]
  },
  "requestId": "uuid"
}
```

状态说明：后续需要权限校验，仅管理员可管理用户。

## Employees 员工管理接口

### 员工模块占位接口

| 项 | 内容 |
| --- | --- |
| 接口说明 | 返回员工模块 placeholder 状态 |
| URL | `/api/employees/` |
| Method | `GET` |
| 状态 | placeholder |

请求参数：无。

请求示例：

```http
GET /api/employees/
```

响应示例：

```json
{
  "code": 0,
  "message": "Employees module placeholder",
  "data": {
    "module": "employees",
    "status": "placeholder"
  },
  "requestId": "uuid"
}
```

状态说明：当前只用于证明路由存在。

### 员工列表

| 项 | 内容 |
| --- | --- |
| 接口说明 | 查询员工档案 |
| URL | `/api/employees/list/` |
| Method | `GET` |
| 状态 | planned |

请求参数：通用分页参数，可增加 `department`、`status`。

请求示例：

```http
GET /api/employees/list/?page=1&pageSize=20&status=active
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "items": [
      {
        "id": 1,
        "employeeNo": "E001",
        "name": "张三",
        "department": "生产部",
        "status": "active"
      }
    ]
  },
  "requestId": "uuid"
}
```

状态说明：用于员工管理和人脸库绑定。

### 创建员工

| 项 | 内容 |
| --- | --- |
| 接口说明 | 新增员工档案 |
| URL | `/api/employees/` |
| Method | `POST` |
| 状态 | planned |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `employeeNo` | string | 是 | 工号 |
| `name` | string | 是 | 姓名 |
| `department` | string | 否 | 部门 |
| `phone` | string | 否 | 手机号 |

请求示例：

```json
{
  "employeeNo": "E001",
  "name": "张三",
  "department": "生产部",
  "phone": "13800000000"
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1
  },
  "requestId": "uuid"
}
```

状态说明：工号重复返回 `409`。

## Face 人脸录入接口

### 人脸录入

| 项 | 内容 |
| --- | --- |
| 接口说明 | 为员工录入人脸图片并生成特征 |
| URL | `/api/face/enroll/` |
| Method | `POST` |
| 状态 | planned |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `employeeId` | number | 是 | 员工 ID |
| `image` | file/base64 | 是 | 人脸图片 |

请求示例：

```json
{
  "employeeId": 1,
  "imageBase64": "data:image/jpeg;base64,..."
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "faceFeatureId": 1,
    "qualityScore": 0.92
  },
  "requestId": "uuid"
}
```

状态说明：图片无人脸或质量过低返回 `422`。

## Cameras 摄像头接口

### 摄像头模块占位接口

| 项 | 内容 |
| --- | --- |
| 接口说明 | 返回摄像头模块 placeholder 状态 |
| URL | `/api/cameras/` |
| Method | `GET` |
| 状态 | placeholder |

请求参数：无。

请求示例：

```http
GET /api/cameras/
```

响应示例：

```json
{
  "code": 0,
  "message": "Cameras module placeholder",
  "data": {
    "module": "cameras",
    "status": "placeholder"
  },
  "requestId": "uuid"
}
```

状态说明：当前只用于证明路由存在。

### 摄像头列表

| 项 | 内容 |
| --- | --- |
| 接口说明 | 查询摄像头配置 |
| URL | `/api/cameras/list/` |
| Method | `GET` |
| 状态 | planned |

请求参数：通用分页参数，可增加 `status`。

请求示例：

```http
GET /api/cameras/list/?status=online
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "items": [
      {
        "id": 1,
        "name": "一号车间入口",
        "streamUrl": "rtsp://example/camera1",
        "playUrl": "http://127.0.0.1:8888/camera1/index.m3u8",
        "status": "online"
      }
    ]
  },
  "requestId": "uuid"
}
```

状态说明：流不可访问时返回离线状态。

### 创建摄像头

| 项 | 内容 |
| --- | --- |
| 接口说明 | 新增摄像头配置 |
| URL | `/api/cameras/` |
| Method | `POST` |
| 状态 | planned |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | 摄像头名称 |
| `location` | string | 否 | 安装位置 |
| `streamUrl` | string | 是 | 原始流地址 |
| `playUrl` | string | 否 | 前端播放地址 |

请求示例：

```json
{
  "name": "一号车间入口",
  "location": "一号车间",
  "streamUrl": "rtsp://example/camera1",
  "playUrl": "http://127.0.0.1:8888/camera1/index.m3u8"
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1
  },
  "requestId": "uuid"
}
```

状态说明：流地址重复或格式错误返回 `409` 或 `400`。

## Zones 警戒区域接口

### 警戒区域模块占位接口

| 项 | 内容 |
| --- | --- |
| 接口说明 | 返回警戒区域模块 placeholder 状态 |
| URL | `/api/zones/` |
| Method | `GET` |
| 状态 | placeholder |

请求参数：无。

请求示例：

```http
GET /api/zones/
```

响应示例：

```json
{
  "code": 0,
  "message": "Zones module placeholder",
  "data": {
    "module": "zones",
    "status": "placeholder"
  },
  "requestId": "uuid"
}
```

状态说明：当前只用于证明路由存在。

### 保存警戒区域

| 项 | 内容 |
| --- | --- |
| 接口说明 | 保存摄像头对应的多边形区域 |
| URL | `/api/zones/` |
| Method | `POST` |
| 状态 | planned |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `cameraId` | number | 是 | 摄像头 ID |
| `name` | string | 是 | 区域名称 |
| `points` | array | 是 | 多边形坐标 |
| `safeDistance` | number | 否 | 安全距离像素阈值 |

请求示例：

```json
{
  "cameraId": 1,
  "name": "危险设备区",
  "points": [
    { "x": 100, "y": 200 },
    { "x": 400, "y": 200 },
    { "x": 420, "y": 520 },
    { "x": 90, "y": 520 }
  ],
  "safeDistance": 20
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1
  },
  "requestId": "uuid"
}
```

状态说明：点位少于 3 个返回 `422`。

## Events 事件日志接口

### 事件模块占位接口

| 项 | 内容 |
| --- | --- |
| 接口说明 | 返回事件模块 placeholder 状态 |
| URL | `/api/events/` |
| Method | `GET` |
| 状态 | placeholder |

请求参数：无。

请求示例：

```http
GET /api/events/
```

响应示例：

```json
{
  "code": 0,
  "message": "Events module placeholder",
  "data": {
    "module": "events",
    "status": "placeholder"
  },
  "requestId": "uuid"
}
```

状态说明：当前只用于证明路由存在。

### 事件列表

| 项 | 内容 |
| --- | --- |
| 接口说明 | 查询监控事件日志 |
| URL | `/api/events/list/` |
| Method | `GET` |
| 状态 | planned |

请求参数：通用分页参数，可增加 `cameraId`、`eventType`、`startTime`、`endTime`。

请求示例：

```http
GET /api/events/list/?cameraId=1&eventType=ZONE_WARNING
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "items": [
      {
        "id": 1,
        "cameraId": 1,
        "eventType": "ZONE_WARNING",
        "level": "high",
        "eventTime": "2026-07-07T10:00:00+08:00"
      }
    ]
  },
  "requestId": "uuid"
}
```

状态说明：用于日志追溯和告警详情跳转。

## Alerts 告警中心接口

### 告警列表

| 项 | 内容 |
| --- | --- |
| 接口说明 | 查询告警中心列表 |
| URL | `/api/alerts/list/` |
| Method | `GET` |
| 状态 | planned |

请求参数：通用分页参数，可增加 `status`、`level`、`eventType`。

请求示例：

```http
GET /api/alerts/list/?status=pending&level=high
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "items": [
      {
        "id": 1,
        "eventId": 10,
        "title": "危险区域入侵",
        "level": "high",
        "status": "pending"
      }
    ]
  },
  "requestId": "uuid"
}
```

状态说明：当前代码尚未建立 `alerts` Django app。

### 告警处置

| 项 | 内容 |
| --- | --- |
| 接口说明 | 确认、处理或关闭告警 |
| URL | `/api/alerts/{alertId}/handle/` |
| Method | `POST` |
| 状态 | planned |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `action` | string | 是 | `confirm`、`processing`、`close` |
| `remark` | string | 否 | 处理说明 |

请求示例：

```json
{
  "action": "close",
  "remark": "现场确认已处理"
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "closed"
  },
  "requestId": "uuid"
}
```

状态说明：非法状态流转返回 `8001`。

## Attendance 考勤接口

### 考勤模块占位接口

| 项 | 内容 |
| --- | --- |
| 接口说明 | 返回考勤模块 placeholder 状态 |
| URL | `/api/attendance/` |
| Method | `GET` |
| 状态 | placeholder |

请求参数：无。

请求示例：

```http
GET /api/attendance/
```

响应示例：

```json
{
  "code": 0,
  "message": "Attendance module placeholder",
  "data": {
    "module": "attendance",
    "status": "placeholder"
  },
  "requestId": "uuid"
}
```

状态说明：当前只用于证明路由存在。

### 考勤记录查询

| 项 | 内容 |
| --- | --- |
| 接口说明 | 查询员工考勤记录 |
| URL | `/api/attendance/records/` |
| Method | `GET` |
| 状态 | planned |

请求参数：通用分页参数，可增加 `employeeId`、`date`。

请求示例：

```http
GET /api/attendance/records/?employeeId=1&date=2026-07-07
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "items": [
      {
        "employeeId": 1,
        "date": "2026-07-07",
        "firstSeenAt": "2026-07-07T08:10:00+08:00",
        "lastSeenAt": "2026-07-07T18:05:00+08:00",
        "leaveCount": 1
      }
    ]
  },
  "requestId": "uuid"
}
```

状态说明：离开/返回检测实现后生成数据。

## AI Results AI 上报接口

### AI 结果模块占位接口

| 项 | 内容 |
| --- | --- |
| 接口说明 | 返回 AI 结果模块 placeholder 状态 |
| URL | `/api/ai-results/` |
| Method | `GET` |
| 状态 | placeholder |

请求参数：无。

请求示例：

```http
GET /api/ai-results/
```

响应示例：

```json
{
  "code": 0,
  "message": "AI results module placeholder",
  "data": {
    "module": "ai_results",
    "status": "placeholder"
  },
  "requestId": "uuid"
}
```

状态说明：当前只用于证明路由存在。

### AI 检测结果上报

| 项 | 内容 |
| --- | --- |
| 接口说明 | AI 服务向后端上报检测结果 |
| URL | `/api/ai-results/report/` |
| Method | `POST` |
| 状态 | planned |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `cameraId` | number | 是 | 摄像头 ID |
| `frameId` | string | 是 | 帧 ID |
| `timestamp` | string | 是 | 检测时间 |
| `results` | array | 是 | 检测结果列表 |

请求示例：

```json
{
  "cameraId": 1,
  "frameId": "frame-0001",
  "timestamp": "2026-07-07T10:00:00+08:00",
  "results": [
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
  ]
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "eventIds": [1],
    "alertIds": []
  },
  "requestId": "uuid"
}
```

状态说明：后端根据结果类型生成事件日志和告警。

## WebSocket 接口

### 实时监控消息

| 项 | 内容 |
| --- | --- |
| 接口说明 | 向前端推送指定摄像头实时 AI 结果和告警状态 |
| URL | `/ws/realtime/{cameraId}/` |
| Method | WebSocket |
| 状态 | planned |

连接参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `cameraId` | number | 是 | 摄像头 ID |
| `token` | string | 是 | 访问凭证，可通过 Header 或 query 传递 |

消息基础格式：

```json
{
  "type": "PERSON_DETECTION",
  "cameraId": 1,
  "timestamp": "2026-07-07T10:00:00+08:00",
  "payload": {}
}
```

消息类型：

| type | 说明 |
| --- | --- |
| `PERSON_DETECTION` | 人员检测结果 |
| `FACE_RESULT` | 人脸识别结果 |
| `HELMET_WARNING` | 头盔异常 |
| `ZONE_WARNING` | 警戒区域异常 |
| `FALL_ALERT` | 摔倒告警 |
| `RUNNING_ALERT` | 异常跑动告警 |
| `EVENT_CREATED` | 事件已生成 |
| `ALERT_UPDATED` | 告警状态已更新 |

消息示例：

```json
{
  "type": "ZONE_WARNING",
  "cameraId": 1,
  "timestamp": "2026-07-07T10:00:00+08:00",
  "payload": {
    "eventId": 12,
    "trackId": "t-1",
    "zoneId": 3,
    "level": "high",
    "footPoint": { "x": 180, "y": 420 }
  }
}
```

状态说明：当前代码未接入 Django Channels 或其他 WebSocket 实现。
