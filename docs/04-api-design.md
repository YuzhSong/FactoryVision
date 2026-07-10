# API 设计

## 当前实现状态

当前后端已实现：

- `GET /api/health/`: implemented
- `POST /api/auth/login/`: implemented
- `POST /api/auth/logout/`: implemented
- `GET /api/auth/me/`: implemented
- `GET /api/users/`: placeholder
- `GET /api/employees/`: placeholder
- `GET /api/cameras/`: placeholder
- `GET /api/cameras/list/`: implemented
- `POST /api/cameras/`: implemented
- `PUT /api/cameras/{id}/`: implemented
- `POST /api/cameras/{id}/toggle/`: implemented
- `GET /api/zones/`: placeholder
- `GET /api/zones/list/`: implemented
- `POST /api/zones/`: implemented
- `GET /api/alerts/list/`: implemented
- `POST /api/alerts/{alertId}/handle/`: implemented
- `GET /api/events/`: placeholder
- `GET /api/attendance/`: placeholder
- `GET /api/ai-results/`: placeholder
- `POST /api/ai-results/report/`: implemented (stub)
- `GET /api/schema/`: implemented
- `GET /api/docs/`: implemented

当前 AI 服务已实现：

- `GET /health`: implemented
- `GET /dependencies`: implemented
- `POST /detect/person`: implemented
- `POST /detect/frame`: implemented
- `POST /process/stream`: implemented
- `POST /streams/start`: implemented
- `POST /streams/stop`: implemented
- `GET /streams/status`: implemented
- `GET /docs`: implemented
- `GET /openapi.json`: implemented

除上述 implemented / placeholder 外，本文档中设计的业务接口均为 `planned`。

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

说明：当前 `common.response.api_response` 默认 `code=200`，placeholder 接口也会使用统一成功码。

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
  "code": 200,
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
| 状态 | implemented |

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
| 状态 | implemented |

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
  "code": 200,
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
| 状态 | implemented |

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
  "code": 200,
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

请求参数：通用分页参数，可增加 `keyword`（模糊匹配姓名或工号）、`department`、`status`。

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
        "position": "操作员",
        "phone": "13800000000",
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
| `position` | string | 否 | 岗位 |
| `phone` | string | 否 | 手机号 |

请求示例：

```json
{
  "employeeNo": "E001",
  "name": "张三",
  "department": "生产部",
  "position": "操作员",
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
| 接口说明 | 为员工批量录入人脸图片（必须 3 张，正脸/左脸/右脸各一张）并生成特征 |
| URL | `/api/face/enroll/` |
| Method | `POST` |
| 状态 | planned |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `employeeId` | number | 是 | 员工 ID |
| `faces` | array | 是 | 人脸图片数组，必须包含 3 项，faceType 分别为 front、left、right |

`faces` 数组每项的字段：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `imageBase64` | string | 是 | 人脸图片 base64 |
| `faceType` | string | 是 | `front`（正面）、`left`（左侧）、`right`（右侧） |

请求示例：

```json
{
  "employeeId": 1,
  "faces": [
    {"imageBase64": "data:image/jpeg;base64,...", "faceType": "front"},
    {"imageBase64": "data:image/jpeg;base64,...", "faceType": "left"},
    {"imageBase64": "data:image/jpeg;base64,...", "faceType": "right"}
  ]
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "results": [
      {"faceType": "front", "faceFeatureId": 1},
      {"faceType": "left",  "faceFeatureId": 2},
      {"faceType": "right", "faceFeatureId": 3}
    ]
  },
  "requestId": "uuid"
}
```

状态说明：

- 全部通过才写入数据库，任意一张失败则整体回滚，返回 `422` 并指明失败原因。
- `faces` 数组不足 3 张或 faceType 缺失返回 `400`。
- 图片无人脸返回 `422`，质量过低返回 `422`，AI 服务不可用返回 `500`。
- 质量判断由 AI Service 内部完成，后端不存储质量分数。

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
  "code": 200,
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
| 接口说明 | 查询摄像头配置，支持关键词搜索和状态筛选。AI Service 不传分页参数时全量返回 |
| URL | `/api/cameras/list/` |
| Method | `GET` |
| 状态 | implemented |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `keyword` | string | 否 | 模糊匹配名称、编码或位置 |
| `status` | string | 否 | online / offline / disabled |
| `page` | number | 否 | 页码，不传返回全量 |
| `pageSize` | number | 否 | 每页数量，默认 20 |

请求示例：

```http
GET /api/cameras/list/?keyword=一号&status=online
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
        "code": "CAM001",
        "streamUrl": "rtmp://srs/live/1",
        "processedStreamUrl": "rtmp://srs/live/1_detected",
        "location": "一号车间南侧",
        "status": "online",
        "enabled": true
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
| 状态 | implemented |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | 摄像头名称 |
| `code` | string | 否 | 编码号，不填自动生成 CAM001 |
| `streamUrl` | string | 是 | 原始 RTMP 流地址 |
| `processedStreamUrl` | string | 否 | AI 处理后带框流地址 |
| `location` | string | 否 | 安装位置 |

请求示例：

```json
{
  "name": "一号车间入口",
  "code": "CAM001",
  "streamUrl": "rtmp://srs/live/1",
  "processedStreamUrl": "rtmp://srs/live/1_detected",
  "location": "一号车间南侧"
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "code": "CAM001"
  },
  "requestId": "uuid"
}
```

状态说明：code 重复返回 `409`，参数错误返回 `400`。

### 编辑摄像头

| 项 | 内容 |
| --- | --- |
| 接口说明 | 编辑摄像头配置，所有字段可选 |
| URL | `/api/cameras/{id}/` |
| Method | `PUT` |
| 状态 | implemented |

请求参数（全部可选，不传保持原值）：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 否 | 摄像头名称 |
| `code` | string | 否 | 编码号 |
| `streamUrl` | string | 否 | 原始流地址 |
| `processedStreamUrl` | string | 否 | AI 处理后流地址 |
| `location` | string | 否 | 安装位置 |
| `enabled` | bool | 否 | 是否启用 |

请求示例：

```json
{
  "name": "一号车间入口（更新）",
  "location": "南侧门"
}
```

响应示例：

```json
{"code": 200, "data": {"id": 1, "code": "CAM001"}}
```

状态说明：摄像头不存在返回 `404`，code 重复返回 `409`。

### 切换摄像头状态

| 项 | 内容 |
| --- | --- |
| 接口说明 | 切换摄像头在线/离线/停用状态 |
| URL | `/api/cameras/{id}/toggle/` |
| Method | `POST` |
| 状态 | implemented |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | string | 是 | online / offline / disabled |

请求示例：

```json
{"status": "online"}
```

响应示例：

```json
{"code": 200, "data": {"id": 1, "status": "online"}}
```

状态说明：摄像头不存在返回 `404`。

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
  "code": 200,
  "message": "Zones module placeholder",
  "data": {
    "module": "zones",
    "status": "placeholder"
  },
  "requestId": "uuid"
}
```

状态说明：当前只用于证明路由存在。

### 区域列表

| 项 | 内容 |
| --- | --- |
| 接口说明 | 查询指定摄像头的警戒区域列表 |
| URL | `/api/zones/list/` |
| Method | `GET` |
| 状态 | implemented |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `cameraId` | string | 否 | 摄像头 ID 或编码 |
| `enabled` | bool | 否 | 是否启用 |

请求示例：

```http
GET /api/zones/list/?cameraId=1
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
        "name": "危险设备区",
        "cameraId": 1,
        "type": "danger",
        "points": [
          {"x": 0.56, "y": 0.45},
          {"x": 0.82, "y": 0.43},
          {"x": 0.87, "y": 0.72}
        ],
        "enabled": true,
        "description": "设备运行危险区域"
      }
    ]
  },
  "requestId": "uuid"
}
```

状态说明：前端选择摄像头后加载对应区域列表，AI Service 也通过此接口获取区域坐标。

### 创建警戒区域

| 项 | 内容 |
| --- | --- |
| 接口说明 | 为摄像头创建多边形警戒区域 |
| URL | `/api/zones/` |
| Method | `POST` |
| 状态 | implemented |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `cameraId` | number | 是 | 摄像头 ID |
| `name` | string | 是 | 区域名称 |
| `type` | string | 否 | restricted/danger/workstation/general，默认 restricted |
| `points` | array | 是 | 多边形坐标，至少 3 个点 |
| `enabled` | bool | 否 | 是否启用，默认 true |
| `description` | string | 否 | 区域说明 |

请求示例：

```json
{
  "cameraId": 1,
  "name": "危险设备区",
  "type": "danger",
  "points": [
    { "x": 100, "y": 200 },
    { "x": 400, "y": 200 },
    { "x": 420, "y": 520 },
    { "x": 90, "y": 520 }
  ],
  "enabled": true,
  "description": "设备运行危险区域"
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

状态说明：点位少于 3 个返回 `422`，摄像头不存在返回 `404`。

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
  "code": 200,
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
| 接口说明 | 查询告警中心列表，支持关键词、等级、状态和时间范围筛选 |
| URL | `/api/alerts/list/` |
| Method | `GET` |
| 状态 | implemented |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `keyword` | string | 否 | 模糊搜索告警标题 |
| `severity` | string | 否 | 等级：info / low / medium / high |
| `status` | string | 否 | 状态：pending / processing / closed |
| `cameraId` | int | 否 | 摄像头 ID |
| `startTime` | string | 否 | 开始时间，ISO 格式 |
| `endTime` | string | 否 | 结束时间，ISO 格式 |
| `page` | int | 否 | 页码，默认 1 |
| `pageSize` | int | 否 | 每页数量，默认 20 |

请求示例：

```http
GET /api/alerts/list/?keyword=入侵&severity=high&status=pending&startTime=2026-07-01T00:00:00&endTime=2026-07-10T23:59:59&page=1&pageSize=20
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
        "title": "危险区域入侵",
        "eventType": "ZONE_INTRUSION",
        "severity": "high",
        "status": "pending",
        "cameraId": 1,
        "cameraName": "一号车间入口",
        "occurredAt": "2026-07-10T14:05:03+08:00",
        "description": "trackId t-1 进入危险设备区"
      }
    ]
  },
  "requestId": "uuid"
}
```

### 告警处置

| 项 | 内容 |
| --- | --- |
| 接口说明 | 处置告警，更新状态（待处理→处理中→已关闭） |
| URL | `/api/alerts/{alertId}/handle/` |
| Method | `POST` |
| 状态 | implemented |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | string | 是 | pending / processing / closed |

请求示例：

```json
{"status": "processing"}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "title": "危险区域入侵",
    "eventType": "ZONE_INTRUSION",
    "severity": "high",
    "status": "processing",
    "cameraId": 1,
    "cameraName": "一号车间入口",
    "occurredAt": "2026-07-10T14:05:03+08:00",
    "description": ""
  },
  "requestId": "uuid"
}
```

状态说明：告警不存在返回 `404`。

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
  "code": 200,
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
  "code": 200,
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
| 状态 | implemented (stub) |

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

当前实现说明：已实现基础字段校验和验收响应，事件生成、告警生成和数据持久化仍为 `planned`。

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "eventIds": [],
    "alertIds": [],
    "acceptedResults": 1,
    "cameraId": 1,
    "frameId": "frame-0001"
  },
  "requestId": "uuid"
}
```

状态说明：后端根据结果类型生成事件日志和告警。

## AI Service Stream 带框流控制接口

以下接口由 AI Service 提供，默认服务地址为 `http://127.0.0.1:9000`。这些接口不属于 Django 后端 `/api/` 路由。

### 启动带框视频流处理

| 项 | 内容 |
| --- | --- |
| 接口说明 | 启动后台任务，从原始 RTMP 流拉帧，检测并画框后回推带框 RTMP 流 |
| URL | `/streams/start` |
| Method | `POST` |
| 状态 | implemented |

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `cameraId` | number/string | 否 | 摄像头 ID，默认 `1` |
| `streamUrl` / `inputUrl` | string | 否 | 原始输入流，默认 `rtmp://81.70.90.222:1935/live/1` |
| `outputUrl` | string | 否 | AI 带框输出流，默认 `rtmp://81.70.90.222:1935/live/1_detected` |
| `playUrl` | string | 否 | 前端播放地址，默认 `webrtc://webrtc.rainycode.cn:8443/live/1_detected` |
| `mode` | string | 否 | `detect` 使用真实检测，`test` 仅画测试框 |
| `includeFaces` | boolean | 否 | 是否执行人脸识别 |
| `reportToBackend` | boolean | 否 | 是否将结构化结果上报后端 |
| `maxFrames` | number | 否 | 调试用最大处理帧数，不传则持续运行 |

请求示例：

```json
{
  "cameraId": 1,
  "streamUrl": "rtmp://81.70.90.222:1935/live/1",
  "outputUrl": "rtmp://81.70.90.222:1935/live/1_detected",
  "playUrl": "webrtc://webrtc.rainycode.cn:8443/live/1_detected",
  "mode": "detect",
  "includeFaces": false,
  "reportToBackend": false
}
```

响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "camera_id": 1,
    "input_url": "rtmp://81.70.90.222:1935/live/1",
    "output_url": "rtmp://81.70.90.222:1935/live/1_detected",
    "play_url": "webrtc://webrtc.rainycode.cn:8443/live/1_detected",
    "mode": "detect",
    "running": true,
    "processed_frames": 0
  }
}
```

### 停止带框视频流处理

| 项 | 内容 |
| --- | --- |
| 接口说明 | 停止当前后台流处理任务 |
| URL | `/streams/stop` |
| Method | `POST` |
| 状态 | implemented |

### 查询带框视频流处理状态

| 项 | 内容 |
| --- | --- |
| 接口说明 | 查询当前 AI 带框流任务运行状态、处理帧数和错误信息 |
| URL | `/streams/status` |
| Method | `GET` |
| 状态 | implemented |

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

状态说明：已接入 Django Channels，AI 上报检测结果后自动推送给对应摄像头的 WebSocket 客户端。
