# 前端设计

## 当前状态

Frontend 使用 Vue 3、Vue Router、Axios、Element Plus、ECharts 和 mpegts.js。所有正式页面已连接 Backend API；实时视频使用 WebRTC 优先、HTTP-FLV 回退，结构化事件通过 WebSocket 接收。

## 页面与路由

| 页面 | 路由 | 主要能力 |
| --- | --- | --- |
| Login | `/login` | 登录、错误提示、Token 保存 |
| Dashboard | `/dashboard` | 告警、事件和摄像头聚合看板 |
| Monitor | `/monitor` | 摄像头选择、带框视频、检测开关、实时事件 |
| Alerts | `/alerts` | 告警筛选、详情、关键帧/回放和处置 |
| Employees | `/employees` | 员工增删改查、三角度人脸录入 |
| Cameras | `/cameras` | 摄像头配置、启停和删除 |
| Zones | `/zones` | 多边形绘制、保存、选择和预览 |
| Reports | `/reports` | AI 监控日报生成、预览和 Word 下载 |

需要登录的页面挂载在 `MainLayout` 下。无 Token 时路由守卫跳转 `/login`；已登录用户访问登录页时跳转 `/dashboard`。

## 实时监控

页面由摄像头列表、视频工作区、实时事件和检测控制组成。人物框由 AIService 强制绘制；四项可选检测以“文字 + 开关”的形式显示：

| 开关 | 启动字段 | 首次默认值 |
| --- | --- | --- |
| 人脸 | `includeFaces` | 关闭 |
| 头盔 | `includeHelmet` | 关闭 |
| 摔倒 | `includeFall` | 关闭 |
| 区域 | `includeZone` | 开启 |

开关状态保存在 `localStorage`，再次进入页面时恢复上次选择。启动流时，配置经 Backend 摄像头流接口传给 AIService；关闭开关会跳过实际检测，不只是隐藏画面元素。

## 视频播放策略

1. 优先使用 SRS WebRTC WHEP 播放低延迟带框流。
2. WebRTC 建连失败或超时后，可切换 HTTP-FLV/mpegts.js。
3. 播放器切换摄像头或页面卸载时销毁旧 PeerConnection、媒体元素和 FLV 实例。
4. HTTP-FLV 采用直播低延迟配置并主动追赶缓冲，避免延迟随播放时间持续增加。
5. 播放地址来自摄像头配置或前端环境变量，不在组件内写死生产域名。

## REST API

`frontend/src/api/http.js` 统一创建 Axios 实例：

```js
baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
```

- 请求拦截器附加 JWT。
- 响应统一读取 `code`、`message`、`data`、`requestId`。
- 业务页面不直接访问 AIService；流启停由 Backend 代理，便于统一鉴权和摄像头配置。
- 文件下载先校验响应确实为 DOCX，再保存，避免把 JSON 错误页当成 Word 文件。

## WebSocket

实时事件地址：

```text
/ws/realtime/{cameraId}/
```

选择摄像头后建立连接，切换摄像头或离开页面时关闭旧连接。新事件按事件 ID 去重后插入事件流；断线时页面展示连接状态，并通过既有重连逻辑恢复。

## 报告预览

日报预览不是在浏览器中直接渲染 DOCX，而是使用报告详情 API 返回的结构化内容，以接近 Word 的白色文档形式展示标题、时段、AI 建议、统计、事件详情和关键帧。下载接口返回实际 DOCX；关键帧无法访问时显示明确占位信息。

## 状态管理

项目未引入全局状态库。登录 Token、当前页面数据和播放器状态保持在 API 封装、`localStorage` 与页面组合式状态中，满足当前规模并降低额外复杂度。

## 验收标准

1. 所有路由可访问，刷新后登录保护和标题正确。
2. 管理页面数据来自 Backend，不依赖硬编码演示数组。
3. 监控页可启动/停止处理流、切换摄像头、记忆检测开关并播放带框流。
4. 告警详情可展示事件证据，缺失媒体时不导致页面失败。
5. 日报可预览并下载有效 DOCX，中文和图片正常。
