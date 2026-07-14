# Camera Management

> **Status:** 新建 —— 后端占位/前端有静态 UI

---

## Requirement: Camera Registration and Management

The system SHALL provide a camera management module for registering, listing, and configuring camera devices that feed video streams into the AI processing pipeline.

### Scenario: Access camera management page — [Status: Implemented — Static UI]

- GIVEN the user is authenticated and navigates to `/cameras`
- WHEN the CamerasView page renders
- THEN the frontend SHALL display a camera table with columns: 名称, 位置, 拉流地址, 播放地址, 状态
- AND the table data SHALL come from hardcoded placeholder data (`data/placeholders.js`) — **Planned: fetch from backend API**
- AND a filter row SHALL be present with status selector and search input
- AND an "新增摄像头" dialog SHALL render form fields: 名称, 位置, 拉流地址 (streamUrl), 播放地址 (playUrl)

### Scenario: List cameras — [Status: Planned]

- GIVEN camera records exist in the database
- WHEN `GET /api/cameras/list/` is called (authenticated)
- THEN the backend SHALL return a paginated list of cameras with fields: `id`, `name`, `location`, `streamUrl`, `playUrl`, `status`

### Scenario: Create a camera — [Status: Planned]

- GIVEN a valid camera configuration payload
- WHEN `POST /api/cameras/` is called
- **Permission model:** TBD — whether this endpoint requires authentication (`IsAuthenticated`) or admin-only access is a future design decision. The backend endpoint is not yet implemented, so this spec does not prescribe a permission rule at this stage.
- THEN a new camera record SHALL be created

### Scenario: Camera placeholder status — [Status: Implemented — Backend Placeholder]

- GIVEN the backend cameras module is running
- WHEN `GET /api/cameras/` is called
- THEN the response SHALL return `{"code": 200, "data": {"module": "cameras", "status": "placeholder"}}`

---

## Camera Data Model — [Status: Planned]

**Note:** 以下字段基于前端 `placeholders.js` 中的硬编码数据推断。后端尚未定义 Camera 模型（`models.py` 为空），正式模型字段以未来实现为准。

| Field | Type | Description |
|-------|------|-------------|
| `name` | — | 摄像头名称 (e.g., "一号车间入口") |
| `location` | — | 物理位置 (e.g., "一号车间") |
| `streamUrl` | — | RTMP/RTSP 拉流地址 (e.g., `rtmp://81.70.90.222:1935/live/1`) |
| `playUrl` | — | WebRTC/HTTP-FLV 播放地址 (e.g., `webrtc://webrtc.rainycode.cn:8443/live/1_detected`) |
| `status` | — | online / offline / disabled |

---

## Hardcoded Reference Data (Current Frontend State)

The frontend currently uses hardcoded camera entries from `data/placeholders.js`:

```javascript
// Camera 1 (functional): streamUrl = rtmp://81.70.90.222:1935/live/1, playUrl = webrtc://webrtc.rainycode.cn:8443/live/1_detected
// Camera 2 (offline):  streamUrl = rtsp://example/camera-02, playUrl = 'planned'
// Camera 3 (disabled): streamUrl = rtsp://example/camera-03, playUrl = 'planned'
```

---

## Constraints

- The camera `streamUrl` is used by `StreamReader` (OpenCV `cv2.VideoCapture`) for RTMP/RTSP ingest.
- The camera `playUrl` is used by `MonitorView.vue` for WebRTC/HTTP-FLV playback.
- The AI service `BackendClient` resolves camera sources from the backend API — currently falling back to environment variable defaults since no camera API exists.

---

## 变更说明

| 说明 |
|------|
| 全新 spec，基于 `backend/apps/cameras/` (placeholder views/serializers/urls) |
| 基于 `frontend/src/views/CamerasView.vue` (完整静态 UI，含新增对话框) |
| 基于 `frontend/src/data/placeholders.js` 中的 3 个硬编码摄像头数据 |
| 基于 `frontend/src/api/modules.js` 中的 `camerasApi` 定义 |
| Camera 数据模型字段基于前端占位数据推断，待后端实现后更新 |
