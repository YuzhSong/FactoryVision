# 前端设计

## 当前状态

当前前端使用 Vue 3 + Vite，已存在基础路由、布局和页面骨架。页面包括 `Login`、`Dashboard`、`Monitor`、`Alerts`、`Employees`、`Cameras`、`Zones`、`Attendance`。实时监控页已接入 SRS WebRTC 播放器，优先播放 AI Service 输出的带框视频流。

## 页面设计

| 页面 | 路由 | 主要内容 | 当前状态 |
| --- | --- | --- | --- |
| Login | `/login` | 用户登录表单、错误提示、登录态保存 | skeleton |
| Dashboard | `/dashboard` | 今日告警、摄像头状态、事件趋势、考勤概览 | skeleton |
| Monitor | `/monitor` | AI 处理后视频流、摄像头列表、实时事件流 | partial implemented |
| Alerts | `/alerts` | 告警列表、筛选、详情、处理动作 | skeleton |
| Employees | `/employees` | 员工档案、人脸录入、状态管理 | skeleton |
| Cameras | `/cameras` | 摄像头配置、流地址、在线状态 | skeleton |
| Zones | `/zones` | 视频画面区域绘制、多边形编辑、区域保存 | skeleton |
| Attendance | `/attendance` | 考勤记录、离开/返回统计、报表 | skeleton |

## 路由设计

当前路由结构：

```text
/login
/
  /dashboard
  /monitor
  /alerts
  /employees
  /cameras
  /zones
  /attendance
```

路由规范：

1. 需要登录的页面统一挂载在 `MainLayout` 下。
2. 登录态失效时跳转到 `/login`。
3. 页面标题应来自路由 `meta.title`。
4. 后续新增页面必须同步更新本设计文档。

## 实时监控大屏布局

实时监控页面采用工作台式布局：

```text
┌────────────────────────────────────────────┐
│ 顶部系统状态：服务状态、在线摄像头、告警数 │
├────────────┬──────────────────┬────────────┤
│ 左侧摄像头 │ 中间带框视频     │ 右侧事件流 │
│ 列表       │ WebRTC 播放器    │ 实时告警   │
├────────────┴──────────────────┴────────────┤
│ 底部统计：人数、陌生人、区域入侵、异常行为 │
└────────────────────────────────────────────┘
```

区域说明：

| 区域 | 内容 |
| --- | --- |
| 顶部系统状态 | 后端状态、AI 服务状态、视频流状态、在线摄像头数量、今日告警数 |
| 左侧摄像头列表 | 摄像头名称、位置、在线状态、快速切换 |
| 中间视频画面 | AI Service 已绘制检测框的 WebRTC 视频流 |
| 右侧实时事件流 | AI 事件、告警等级、发生时间、快捷处理入口 |
| 底部统计信息 | 当前人数、陌生人数、区域入侵次数、安全行为异常次数 |

## 关键组件划分

| 组件 | 职责 | 当前状态 |
| --- | --- | --- |
| `MainLayout` | 主导航、页面容器、整体布局 | skeleton |
| `CameraList` | 摄像头列表和状态切换 | planned |
| `VideoPlayer` | 播放 SRS WebRTC 带框视频流 | partial implemented |
| `DetectionOverlay` | 前端叠加 bbox 能力，当前 B 方案暂不启用 | planned |
| `RealtimeEventFeed` | 展示 WebSocket 实时事件 | planned |
| `ZoneEditor` | 绘制和编辑多边形警戒区域 | planned |
| `AlertTable` | 告警列表、筛选和状态标签 | planned |
| `AlertDetailDrawer` | 告警详情和处理记录 | planned |
| `EmployeeForm` | 员工新增和编辑 | planned |
| `FaceEnrollUploader` | 人脸图片上传和质量提示 | planned |
| `DashboardCharts` | ECharts 指标和趋势图 | planned |

## REST API 消费方式

当前 `frontend/src/api/http.js` 已封装 axios 实例：

```js
baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
```

前端调用规范：

1. 所有业务请求通过统一 HTTP 实例发起。
2. 不允许前端直连数据库。
3. API 响应统一读取 `code`、`message`、`data`、`requestId`。
4. 业务错误需要展示明确提示，并记录 `requestId` 便于排查。
5. 列表页面使用统一分页参数 `page`、`pageSize`、`keyword`。

## WebSocket 消息消费方式

实时监控页面 planned WebSocket 地址：

```text
/ws/realtime/{cameraId}/
```

消费流程：

1. 用户选择摄像头。
2. 前端建立对应摄像头的 WebSocket 连接。
3. 当前 B 方案中检测框已由 AI Service 写入视频帧，前端不再实时绘制 bbox。
4. 收到 `FACE_RESULT` 后更新人员标签。
5. 收到 `ZONE_WARNING`、`HELMET_WARNING`、`FALL_ALERT`、`RUNNING_ALERT` 后加入右侧事件流。
6. 收到 `EVENT_CREATED` 后可刷新事件统计。
7. 收到 `ALERT_UPDATED` 后同步告警状态。
8. 摄像头切换或页面离开时关闭旧连接。

## 状态管理建议

| 状态 | 来源 | 用途 |
| --- | --- | --- |
| 登录用户 | 登录 API | 权限、导航、用户信息 |
| 摄像头列表 | REST API | 监控页、区域配置 |
| 当前摄像头 | 用户选择 | 视频播放和 WebSocket 连接 |
| 实时检测结果 | WebSocket | 视频叠加层 |
| 实时事件流 | WebSocket | 右侧事件列表和告警提示 |
| 告警列表 | REST API | 告警中心 |
| 字典配置 | REST API | 状态、等级、事件类型展示 |

## 页面验收标准

1. 页面路由可正常访问，刷新后路径保持正确。
2. 页面在后端接口未实现时展示空状态或 placeholder，不阻断操作。
3. 实时监控布局在桌面分辨率下信息层次清晰。
4. 所有业务数据通过后端 API 或 WebSocket 获取。
5. 接口字段变更时同步更新 `04-api-design.md` 和本文件。
