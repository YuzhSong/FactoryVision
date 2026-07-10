# Camera Management

> **Status:** Implemented — 后端 CRUD + 前端列表/筛选已接入

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Camera Management in the Factory Vision system.

---

## Requirements

### Requirement: Camera list and search

The backend SHALL provide a camera list endpoint with keyword search, status filtering, and pagination. AI Service SHALL receive full results when omitting pagination parameters.

#### Scenario: List all cameras

- **GIVEN** camera records exist in the database
- **WHEN** `GET /api/cameras/list/` is called without pagination parameters
- **THEN** the backend SHALL return all cameras with fields: `id`, `name`, `code`, `streamUrl`, `processedStreamUrl`, `location`, `status`, `enabled`
- **AND** AI Service SHALL use this endpoint to discover camera stream URLs

#### Scenario: Search and filter cameras

- **GIVEN** the user is on the camera management page
- **WHEN** `GET /api/cameras/list/?keyword=车间&status=online&page=1&pageSize=20` is called
- **THEN** the backend SHALL return paginated results filtered by keyword (matches name, code, or location) and status
- **AND** status filter accepts `online`, `offline`, `disabled`

### Requirement: Camera creation

The backend SHALL provide a camera creation endpoint with auto-generated code when not provided.

#### Scenario: Create camera with explicit code

- **GIVEN** the user is authenticated
- **WHEN** `POST /api/cameras/` is called with `{name, code:"CAM001", streamUrl, processedStreamUrl, location}`
- **THEN** the backend SHALL create a new camera record
- **AND** return `{id, code}` with HTTP 200

#### Scenario: Create camera without code

- **GIVEN** the user is authenticated
- **WHEN** `POST /api/cameras/` is called without a `code` field
- **THEN** the backend SHALL auto-generate a code in `CAM00N` format
- **AND** return `{id, code}` with HTTP 200

#### Scenario: Duplicate code rejected

- **GIVEN** a camera with code "CAM001" already exists
- **WHEN** `POST /api/cameras/` is called with `code:"CAM001"`
- **THEN** the backend SHALL return HTTP 409 with message "编码 CAM001 已存在"

### Requirement: Camera editing

The backend SHALL provide a camera update endpoint where all fields are optional.

#### Scenario: Partial update

- **GIVEN** the user is authenticated and camera id=1 exists
- **WHEN** `PUT /api/cameras/{id}/` is called with `{name:"新名称", location:"新位置"}`
- **THEN** the backend SHALL update only those fields, leaving others unchanged
- **AND** return `{id, code}` with HTTP 200

#### Scenario: Code conflict on update

- **GIVEN** cameras with codes "CAM001" (id=1) and "CAM002" (id=2)
- **WHEN** `PUT /api/cameras/1/` is called with `{code:"CAM002"}`
- **THEN** the backend SHALL return HTTP 409

### Requirement: Camera status toggle

The backend SHALL provide a status toggle endpoint for switching camera online/offline/disabled state.

#### Scenario: Toggle camera online

- **GIVEN** a camera with status "offline"
- **WHEN** `POST /api/cameras/{id}/toggle/` is called with `{status:"online"}`
- **THEN** the backend SHALL update the camera status and return `{id, status}`

---

## Camera Data Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAuto | Primary key |
| `name` | CharField(128) | 摄像头名称 |
| `code` | CharField(64), unique | 唯一编码，可自动生成 CAM00N |
| `stream_url` | CharField(512) | 原始 RTMP 流地址，AI Service 拉流用 |
| `processed_stream_url` | CharField(512) | AI 处理后带框 RTMP 地址，前端播放用 |
| `location` | CharField(255) | 安装位置 |
| `status` | CharField(32) | online / offline / disabled，默认 offline |
| `enabled` | BooleanField | 是否启用，默认 true |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

---

## API Endpoints

| Method | URL | Description | Auth |
|--------|-----|-------------|------|
| `GET` | `/api/cameras/list/` | 摄像头列表（支持 keyword/status/page/pagesize） | No |
| `POST` | `/api/cameras/` | 创建摄像头 | Bearer JWT |
| `PUT` | `/api/cameras/{id}/` | 编辑摄像头（所有字段可选） | Bearer JWT |
| `POST` | `/api/cameras/{id}/toggle/` | 切换在线/离线/停用状态 | Bearer JWT |

---

## Constraints

- `stream_url` is used by AI Service `StreamReader` (OpenCV `cv2.VideoCapture`) for RTMP ingest.
- `processed_stream_url` is used by the frontend for WebRTC playback of AI-detected streams.
- AI Service `BackendClient.list_cameras()` calls this endpoint without pagination to receive full camera list.
- Frontend `CamerasView.vue` calls this endpoint with pagination and optional keyword/status filters.
- Status `online`/`offline`/`disabled` is managed by the toggle endpoint; AI Service detects actual stream health separately.

---

## 变更说明

| 说明 |
|------|
| 从 placeholder 升级为完整 CRUD 实现 |
| 模型从文档的 `playUrl` 改为 `processed_stream_url`，对应 AI 处理后带框流 |
| 新增 `code` 唯一编码，支持手动输入或自动生成 CAM00N |
| 列表增加 keyword 搜索和分页，AI Service 不传 page 获得全量 |
| Swagger 注解使用中文 |
