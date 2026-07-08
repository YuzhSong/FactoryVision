# 通讯接口待办需求与详细分析单

## 1. 文档目的

本文档用于 FactoryVision 项目三端联调对接：

- `frontend`：Vue 前端
- `backend`：Django + DRF 后端
- `ai-service`：FastAPI AI 服务
- `video-stream`：当前实际依赖 SRS 作为视频转发与播放分发服务

本文档重点覆盖以下 6 条通讯需求：

1. Django 录入人脸后，调用 AI 服务提取特征向量并写回存储
2. AI 服务实时将画面与画面内标注传递给 Vue
3. AI 服务检测到异常/报警后，将结果发送给 Django 入库，供前端读取
4. AI 服务启动时，从 Django 一次性加载业务数据并缓存
5. 后端员工信息增删改后，通知 AI 服务更新缓存
6. AI 服务持续拉取视频转发服务器帧流并做抽帧分析

本文档同时说明：

- 当前仓库已经实现了什么
- 当前没有实现什么
- 推荐新增哪些接口
- 每个接口的调用方向、触发时机、字段建议、验收标准

## 2. 当前结论总览

### 2.1 已实现的通讯能力

- `Vue -> Django` 的基础 REST 调用已具备，前端通过 `axios` 调 Django API
- `ai-service -> Django` 的基础 HTTP 调用已具备，AI 服务通过 `requests.Session()` 调后端 API
- `ai-service` 持续拉取视频流、分析、画框、推送处理后视频流的能力已具备
- `Vue <- SRS` 播放处理后视频流的能力已具备
- `ai-service -> Django` 的 AI 结果上报入口骨架已存在
- `ai-service <- Django` 的员工列表读取骨架已存在

### 2.2 未实现或仅有骨架的能力

- Django 录入人脸并调用 AI 提取特征向量：未实现
- Django 存储员工人脸特征向量：未实现
- Django 反向通知 AI 刷新缓存：未实现
- AI 启动即自动全量预加载缓存：未实现
- 后端事件/告警真实入库：未实现
- 前端实时接收结构化标注和实时事件：未实现
- WebSocket 实时消息通道：前端预留，后端未实现
- 摄像头、区域、告警、考勤等多数业务接口：前端已预留调用名，后端未实际落地

### 2.3 建议的目标架构

建议将通讯拆成 3 类，不要混用：

1. 业务数据通道
   - 走 Django REST API
   - 用于员工、摄像头、区域、告警、事件、考勤、缓存同步控制

2. 实时结构化消息通道
   - 走 Django WebSocket
   - 用于实时框信息、实时告警、实时统计、缓存刷新通知回执

3. 视频媒体通道
   - 继续走 `视频源 -> SRS -> ai-service -> SRS -> Vue`
   - 不建议把视频帧本身塞进 WebSocket

## 3. 当前代码现状拆解

## 3.1 Vue -> Django

前端当前通过 `frontend/src/api/http.js` 统一配置 `baseURL` 和 JWT 请求头，通过 `frontend/src/api/modules.js` 定义模块 API 名称。

实际情况：

- 登录相关接口已接通
- 员工列表、摄像头列表、区域列表、告警列表、考勤列表等很多接口名已经在前端写好
- 但后端很多对应路由并不存在，或者只是 placeholder

结论：

- 前端 API 命名层已经有基础
- 真实业务接口仍需后端逐个补齐

## 3.2 ai-service -> Django

AI 服务当前通过 `modules/backend_client.py` 访问后端，具备以下骨架能力：

- 拉员工列表
- 拉摄像头列表
- 拉区域列表
- 上报 AI 检测结果

结论：

- AI 服务和 Django 之间的基础 HTTP request-response 模式已经确定
- 但后端对应的数据模型和大部分真实接口尚未落地

## 3.3 ai-service -> Vue

当前并不是 `ai-service` 直接把视频与标注通过单一长连接推给 Vue，而是：

- `ai-service` 从视频源或 SRS 拉流
- `ai-service` 在服务内画框
- `ai-service` 再通过 FFmpeg 把处理后视频推回 SRS
- `Vue` 从 SRS 以 `HTTP-FLV` 或 `WebRTC` 播放

这条链路已经满足“带框视频实时展示”，但并不满足“结构化标注实时传输”。

结论：

- 视频流通道已可用
- 结构化标注通道还缺失

## 4. 需求逐项分析与待办接口

## 4.1 需求一：Django 录入人脸后，调用 AI 服务进行特征向量分析并存入

### 4.1.1 目标

当后端新增员工人脸图片后，应由后端发起调用 AI 服务，完成：

- 人脸检测
- 特征向量提取
- 人脸质量校验
- 特征向量持久化
- AI 缓存同步

### 4.1.2 当前现状

- 后端只有员工基础信息模型，没有人脸特征模型
- 前端员工页只有“录入占位”
- 前端预留了 `faceApi.enroll()`，但后端没有 `/api/face/enroll/`
- AI 服务内部有 `extract_feature()` 能力，但没有对外的“录入提特征”接口
- 后端没有任何调用 AI 服务的客户端封装

### 4.1.3 建议流程

```text
Vue -> Django: 上传员工人脸图
Django -> 存原图
Django -> ai-service: 请求提取特征向量
ai-service -> Django: 返回 featureVector、质量信息
Django -> DB: 写入员工人脸特征记录
Django -> ai-service: 请求增量刷新缓存或直接推送 upsert
```

### 4.1.4 建议新增接口

#### A. 前端录入人脸接口

- `POST /api/employees/{employeeId}/faces/`
- 调用方：Vue
- 服务方：Django
- 作用：上传员工人脸原图并触发后续提特征流程

请求建议：

```json
{
  "source": "upload",
  "imageBase64": "base64-data",
  "remark": "front face"
}
```

也可改为 `multipart/form-data` 上传文件。

响应建议：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "faceRecordId": 101,
    "employeeId": 1,
    "featureStatus": "processing"
  }
}
```

#### B. Django 调 AI 提取特征接口

- `POST /faces/extract`
- 调用方：Django
- 服务方：ai-service
- 作用：输入图片，返回归一化特征向量和质量信息

请求建议：

```json
{
  "employeeId": 1,
  "employeeNo": "E001",
  "name": "张三",
  "imageUrl": "https://backend/media/employees/1/front.jpg"
}
```

响应建议：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "employeeId": 1,
    "faceCount": 1,
    "featureVector": [0.123, -0.456, 0.789],
    "dimension": 512,
    "qualityScore": 0.93,
    "faceBox": {
      "x1": 120,
      "y1": 130,
      "x2": 210,
      "y2": 240
    }
  }
}
```

错误场景建议：

- 未检测到人脸
- 检测到多张人脸
- 图片模糊，质量过低
- 特征向量生成失败

#### C. 员工人脸详情查询接口

- `GET /api/employees/{employeeId}/faces/`
- 调用方：Vue
- 服务方：Django
- 作用：查看已录入的人脸记录、状态和最新特征提取结果

### 4.1.5 建议数据模型

后端至少新增：

- `EmployeeFace`
  - `id`
  - `employee_id`
  - `image_path`
  - `status`：`pending/success/failed/disabled`
  - `quality_score`
  - `created_at`
  - `updated_at`

- `EmployeeFaceFeature`
  - `id`
  - `employee_face_id`
  - `feature_vector`
  - `dimension`
  - `model_name`
  - `version`
  - `created_at`

### 4.1.6 是否已实现

- 已实现：AI 服务内部具备特征提取能力
- 未实现：对外提取接口、后端调用、后端存储、前端录入闭环

### 4.1.7 验收标准

- 上传员工人脸后，5 秒内能完成特征提取和存储
- 同一员工可有多张人脸图
- AI 缓存同步后，新员工可参与实时识别
- 失败时前端能看到明确失败原因

## 4.2 需求二：AI 服务实时将画面与画面内标注传输到 Vue

### 4.2.1 目标

Vue 监控页需要同时拿到：

- 实时视频画面
- 实时标注框、轨迹、识别结果、告警结果等结构化数据

### 4.2.2 当前现状

- 带框视频流已可从 SRS 播放
- 画面内标注已被 AI 直接画进视频帧
- 结构化标注数据没有实时通道
- 前端虽有 `createRealtimeConnection()`，但 Django 端没有 WebSocket 实现

### 4.2.3 建议实现策略

不要让浏览器直接连 `ai-service` 收结构化数据，推荐：

1. 视频仍走 SRS
2. 结构化标注走 Django WebSocket
3. `ai-service -> Django` 实时推送标注消息
4. Django 做认证、转发、房间广播
5. Vue 只连 Django WebSocket

这样更利于：

- 鉴权
- 多前端订阅
- 后端统一日志与限流
- 以后接第三方客户端

### 4.2.4 建议新增接口

#### A. AI 实时标注上报接口

- `POST /api/realtime/frame-results/`
- 调用方：ai-service
- 服务方：Django
- 作用：上报某一帧的结构化标注结果，供 Django 广播到 WebSocket

请求建议：

```json
{
  "cameraId": 1,
  "frameId": "frame-000123",
  "timestamp": "2026-07-08T10:00:00+08:00",
  "playbackUrl": "webrtc://example/live/1_detected",
  "results": [
    {
      "type": "PERSON_DETECTION",
      "trackId": "t-1",
      "bbox": { "x1": 100, "y1": 120, "x2": 220, "y2": 360 },
      "confidence": 0.96
    },
    {
      "type": "FACE_RESULT",
      "trackId": "t-1",
      "employeeId": 1,
      "name": "张三",
      "matched": true,
      "similarity": 0.92
    }
  ]
}
```

说明：

- 该接口不要求持久化
- 该接口主要用于实时广播
- 可以设置采样频率，例如每秒 2 到 5 次

#### B. 前端实时订阅接口

- `WS /ws/realtime/cameras/{cameraId}/`
- 调用方：Vue
- 服务方：Django
- 作用：订阅某摄像头的实时标注、告警和状态消息

消息体建议：

```json
{
  "messageType": "frame_results",
  "cameraId": 1,
  "frameId": "frame-000123",
  "timestamp": "2026-07-08T10:00:00+08:00",
  "results": []
}
```

### 4.2.5 是否已实现

- 已实现：带框视频流链路
- 未实现：结构化实时标注通道、Django WebSocket、前端实时消费

### 4.2.6 验收标准

- 前端可实时看到处理后视频
- 前端可独立获取同帧标注数据
- WebSocket 断线可重连
- 单摄像头多客户端订阅互不影响

## 4.3 需求三：AI 服务检测到异常和报警后，将信息发送给 Django 写入，供前端读取

### 4.3.1 目标

AI 服务对实时流分析后，识别出的异常事件和告警，应进入 Django 持久化层，供：

- 告警中心页面查询
- 大屏/仪表盘统计
- 事件追溯
- 人工处理闭环

### 4.3.2 当前现状

- `POST /api/ai-results/report/` 已有骨架
- 当前只做 serializer 校验并返回 accepted
- 没有事件表、告警表、处理记录表
- 前端告警页仍是本地假数据

### 4.3.3 建议流程

```text
ai-service -> Django: 上报 AI 结果
Django -> DB: 写事件、写告警、做去重
Django -> WebSocket: 广播新告警
Vue -> Django: 查询告警列表/详情/处理状态
```

### 4.3.4 建议保留并增强的接口

#### A. AI 结果上报接口

- `POST /api/ai-results/report/`
- 调用方：ai-service
- 服务方：Django
- 作用：AI 结构化结果统一入库入口

请求体建议沿用当前结构，但需扩展标准字段：

```json
{
  "cameraId": 1,
  "frameId": "frame-000321",
  "timestamp": "2026-07-08T10:01:11+08:00",
  "results": [
    {
      "type": "ZONE_WARNING",
      "trackId": "t-1",
      "level": "high",
      "zoneId": 3,
      "zoneName": "危险设备区",
      "inside": true,
      "distance": 0
    }
  ]
}
```

响应建议：

```json
{
  "code": 200,
  "message": "AI results accepted",
  "data": {
    "eventIds": [1001],
    "alertIds": [5001],
    "acceptedResults": 1,
    "cameraId": 1,
    "frameId": "frame-000321"
  }
}
```

#### B. 告警列表接口

- `GET /api/alerts/list/`
- 调用方：Vue
- 服务方：Django

#### C. 告警详情接口

- `GET /api/alerts/{alertId}/`

#### D. 告警处理接口

- `POST /api/alerts/{alertId}/handle/`

请求建议：

```json
{
  "action": "confirm",
  "remark": "已通知现场人员处理"
}
```

### 4.3.5 建议数据模型

- `AIEvent`
  - 原始 AI 结果记录
  - 包含 `camera_id`, `frame_id`, `result_type`, `payload_json`, `occurred_at`

- `Alert`
  - 告警聚合记录
  - 包含 `level`, `status`, `camera_id`, `event_id`, `title`, `description`

- `AlertHandleRecord`
  - 人工处理流水
  - 包含 `alert_id`, `action`, `operator_id`, `remark`, `created_at`

### 4.3.6 是否已实现

- 已实现：AI 上报入口 URL
- 未实现：真实持久化、查询接口、处理闭环、前端读取闭环

### 4.3.7 验收标准

- AI 识别到告警后，1 秒内写入数据库
- 前端告警列表能查到新告警
- 同类告警可做基本去重或合并策略
- 告警处理状态可追踪

## 4.4 需求四：AI 服务启动时，一次性从 Django 读入数据并加载至缓存区

### 4.4.1 目标

AI 服务在启动时一次性拿到运行所需基础数据，避免首次请求时才懒加载。

建议至少预加载：

- 员工人脸特征
- 摄像头配置
- 区域配置
- AI 参数配置

### 4.4.2 当前现状

- `POST /faces/reload` 可手动从 backend 拉员工数据
- `/process/stream` 在带 `cameraId` 时可懒加载员工数据
- 没有 startup hook 自动预热
- 也没有统一 bootstrap 接口

### 4.4.3 建议流程

```text
ai-service 启动
ai-service -> Django: 获取 bootstrap 数据
ai-service -> 本地内存缓存
ai-service: 标记 cacheReady=true
```

### 4.4.4 建议新增接口

#### A. 启动全量加载接口

- `GET /api/ai/bootstrap/`
- 调用方：ai-service
- 服务方：Django
- 作用：一次性返回 AI 启动所需数据

响应建议：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "version": "2026-07-08T10:00:00+08:00",
    "employees": [],
    "cameras": [],
    "zones": [],
    "settings": {
      "faceSimilarityThreshold": 0.45,
      "runningSpeedThreshold": 120.0
    }
  }
}
```

说明：

- 若数据量过大，可拆成多个接口
- 但联调初期更建议先提供一个聚合接口，减少网络往返和对接复杂度

### 4.4.5 AI 本地缓存建议

AI 服务应维护至少 4 类缓存：

- `employee_face_cache`
- `camera_config_cache`
- `zone_cache_by_camera`
- `system_settings_cache`

### 4.4.6 是否已实现

- 已实现：按需懒加载员工信息
- 未实现：启动自动加载、全量 bootstrap 接口、统一缓存状态

### 4.4.7 验收标准

- AI 服务启动后无需等待首个识别请求再拉基础数据
- 健康检查里能体现 `cacheReady`
- 后端数据为空时也能正确启动

## 4.5 需求五：后端有新的员工信息增删改时，通知 AI 服务更新缓存

### 4.5.1 目标

当后端员工、人脸、区域、摄像头配置发生变更时，AI 缓存应增量更新，而不是每次全量 reload。

### 4.5.2 当前现状

- 后端没有反向调用 AI 的能力
- AI 只有手动 `POST /faces/reload`
- 没有 webhook、消息队列、outbox、重试机制

### 4.5.3 建议实现策略

联调一期建议直接使用 Django 调 AI 的 HTTP webhook，不需要一开始就引入消息队列。

推荐做两层：

1. 业务保存成功后，写一条同步任务
2. 由 Django 异步或后台任务调用 AI 缓存接口

### 4.5.4 建议新增接口

#### A. AI 增量 upsert 接口

- `POST /cache/employees/upsert`
- 调用方：Django
- 服务方：ai-service
- 作用：新增或更新员工及其人脸特征缓存

请求建议：

```json
{
  "version": "2026-07-08T10:20:00+08:00",
  "employees": [
    {
      "id": 1,
      "employeeNo": "E001",
      "name": "张三",
      "status": "active",
      "faceFeatures": [
        {
          "id": 101,
          "featureVector": [0.123, -0.456, 0.789]
        }
      ]
    }
  ]
}
```

#### B. AI 删除员工缓存接口

- `POST /cache/employees/delete`
- 调用方：Django
- 服务方：ai-service

请求建议：

```json
{
  "employeeIds": [1, 2]
}
```

#### C. AI 区域缓存刷新接口

- `POST /cache/zones/reload`

#### D. AI 摄像头缓存刷新接口

- `POST /cache/cameras/reload`

### 4.5.5 反向调用时机

建议以下动作触发缓存同步：

- 新增员工
- 编辑员工基础信息
- 上传新的人脸图
- 启用/停用员工
- 删除员工
- 编辑区域
- 编辑摄像头推流/播放配置

### 4.5.6 是否已实现

- 已实现：无
- 未实现：Django 到 AI 的缓存同步全链路

### 4.5.7 验收标准

- 员工新增后，AI 在 5 秒内可识别
- 员工停用后，AI 不再继续命中旧身份
- 删除员工后，缓存中不残留该员工向量

## 4.6 需求六：AI 服务持续拉取视频转发服务器帧流并进行抽帧分析

### 4.6.1 目标

AI 服务持续从视频转发服务或摄像头源头拉流，按节流策略抽帧，执行检测与告警判断。

### 4.6.2 当前现状

该能力已经基本完成。

现有能力包括：

- 通过 OpenCV `VideoCapture` 持续拉流
- 断流自动重连
- 捕获线程与处理线程分离
- 只保留最新帧，丢弃旧帧，控制延迟
- 通过 `FRAME_DETECT_INTERVAL` 抽帧做重检测
- 处理后回推 RTMP

### 4.6.3 仍建议补充的点

- 后端真实摄像头列表接口
- 摄像头状态回写接口
- AI 处理任务控制接口是否由 Django 统一编排
- 流任务生命周期记录

### 4.6.4 建议接口

#### A. 摄像头列表接口

- `GET /api/cameras/list/`
- 调用方：ai-service 或 Vue
- 服务方：Django

#### B. 摄像头状态回写接口

- `POST /api/cameras/{cameraId}/stream-status/`
- 调用方：ai-service
- 服务方：Django

请求建议：

```json
{
  "status": "online",
  "captureFps": 24.1,
  "processFps": 9.8,
  "droppedFrames": 38,
  "latestFrameAgeMs": 112.4,
  "lastError": ""
}
```

### 4.6.5 是否已实现

- 已实现：AI 服务内部持续拉流、抽帧、分析、回推
- 未实现：与后端真实摄像头配置和状态管理的完整闭环

### 4.6.6 验收标准

- AI 服务可稳定持续处理实时流
- 延迟不随时间持续累积
- 断流可重连
- 状态数据可被后端与前端读取

## 5. 推荐新增接口清单

以下为建议对接清单，按优先级排序。

### 5.1 P0 必须先做

- `POST /api/employees/{employeeId}/faces/`
- `POST /faces/extract`
- `GET /api/ai/bootstrap/`
- `POST /cache/employees/upsert`
- `POST /cache/employees/delete`
- `POST /api/ai-results/report/` 真正入库版
- `GET /api/alerts/list/`
- `WS /ws/realtime/cameras/{cameraId}/`

### 5.2 P1 建议尽快做

- `GET /api/employees/{employeeId}/faces/`
- `POST /api/realtime/frame-results/`
- `POST /cache/zones/reload`
- `POST /cache/cameras/reload`
- `GET /api/cameras/list/`
- `GET /api/zones/list/`
- `GET /api/alerts/{alertId}/`
- `POST /api/alerts/{alertId}/handle/`

### 5.3 P2 后续补充

- `POST /api/cameras/{cameraId}/stream-status/`
- `GET /api/events/list/`
- `GET /api/attendance/records/`
- `POST /api/ai-service/heartbeat/`

## 6. 建议消息格式规范

## 6.1 统一时间格式

- 一律使用 ISO 8601
- 例：`2026-07-08T10:00:00+08:00`

## 6.2 统一主键字段

- 员工：`employeeId`
- 摄像头：`cameraId`
- 区域：`zoneId`
- 告警：`alertId`
- 事件：`eventId`
- 人脸记录：`faceRecordId`

## 6.3 统一结果类型

- `PERSON_DETECTION`
- `FACE_RESULT`
- `HELMET_WARNING`
- `ZONE_WARNING`
- `FALL_ALERT`
- `RUNNING_ALERT`

## 6.4 统一告警级别

- `low`
- `medium`
- `high`

## 6.5 统一状态字段

- 员工：`active/inactive`
- 告警：`pending/processing/closed`
- 人脸特征：`pending/success/failed`
- 摄像头：`online/offline/disabled`

## 7. 三端分工建议

## 7.1 Django 后端

负责：

- 新增真实业务模型
- 实现人脸录入与特征存储
- 实现 AI bootstrap 接口
- 实现 AI 结果入库
- 实现告警查询与处理
- 实现 WebSocket 广播层
- 实现反向调用 AI 的客户端

## 7.2 ai-service

负责：

- 新增 `POST /faces/extract`
- 新增缓存增量更新接口
- 新增启动预热逻辑
- 新增实时标注上报逻辑
- 持续保留流分析与回推能力

## 7.3 Vue 前端

负责：

- 员工人脸录入页
- 实时监控页 WebSocket 消费
- 告警中心对接真实接口
- 员工、摄像头、区域页面切换到真实数据源

## 8. 联调实施顺序

建议按以下顺序推进，避免互相阻塞。

### 第一阶段：打通员工人脸录入闭环

1. Django 增加员工人脸与特征模型
2. ai-service 增加 `/faces/extract`
3. Django 增加 `/api/employees/{employeeId}/faces/`
4. Vue 员工页接入录入流程

### 第二阶段：打通 AI 缓存同步闭环

1. Django 增加 `/api/ai/bootstrap/`
2. ai-service 增加启动预热
3. ai-service 增加 `/cache/employees/upsert` 和 `/cache/employees/delete`
4. Django 在员工变更后回调 AI

### 第三阶段：打通告警入库与前端查询闭环

1. Django 完成 `ai-results/report` 入库逻辑
2. Django 增加 `alerts/list`、`alerts/{id}`、`alerts/{id}/handle`
3. Vue 告警页接真实接口

### 第四阶段：打通实时结构化消息闭环

1. Django 增加 WebSocket
2. ai-service 增加实时 frame-results 上报
3. Vue 监控页接入 WebSocket

## 9. 主要风险与注意事项

- 不建议让 Vue 直接调用 AI 业务接口，鉴权、审计和扩展性都较差
- 不建议把视频帧通过 WebSocket 传给前端，带宽和浏览器压力都高
- AI 结果入库时应有去重策略，否则同一目标每帧都会生成大量重复告警
- 员工特征向量建议版本化，便于模型升级后重刷
- 后端反向调用 AI 时应有重试和失败记录，避免保存成功但缓存未更新
- 员工列表接口当前要求 JWT，AI 服务需要独立的后端访问认证方案

## 10. 最终对接结论

当前项目已经具备：

- `Vue -> Django` 的基础 REST 骨架
- `ai-service -> Django` 的基础 HTTP 骨架
- `ai-service -> SRS -> Vue` 的实时带框视频链路
- `ai-service` 持续拉流与抽帧分析能力

当前项目尚未具备：

- Django 录入人脸并调用 AI 提特征的闭环
- Django 持久化员工特征向量的能力
- Django 反向通知 AI 更新缓存的能力
- AI 启动自动全量预加载缓存的能力
- Django 对 AI 结果的真实入库与告警闭环
- Vue 获取实时结构化标注和实时告警的能力

因此，对外协作时可以明确说明：

- 视频流处理主链已经有基础
- 业务数据链和实时消息链仍需补齐
- 联调优先级应先做人脸录入闭环，再做缓存同步，再做告警入库，最后做实时结构化消息
