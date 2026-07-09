# AI Results Reporting

> **Status:** 新建 —— 基于已实现的 AI 上报端点

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for AI Results Reporting in the Factory Vision system.


## Requirements

### Requirement: AI Detection Result Reporting

The system SHALL provide a backend endpoint for the AI service to report detection results. The endpoint SHALL validate the payload structure and return acceptance confirmation.

#### Scenario: Report AI detection results — [Status: Implemented]

- GIVEN the AI service has processed a video frame and produced detection results
- WHEN `POST /api/ai-results/report/` is called with a valid JSON payload
- THEN the backend SHALL validate required fields:
  - `cameraId`: integer >= 1
  - `frameId`: string (no length/non-empty constraint, only the type is validated)
  - `timestamp`: valid ISO 8601 datetime string
  - `results`: list of result objects (may be empty — `allow_empty=True`)
- AND upon success SHALL return `{"code": 200, "data": {"acceptedResults": <int>, "eventIds": [], "alertIds": [], "cameraId": <int>, "frameId": "<str>"}}`
- **Note:** Results are validated and accepted but NOT persisted to the database (no AI result models exist yet)

#### Scenario: Reject invalid AI report — [Status: Implemented]

- GIVEN an invalid payload (missing required field, wrong type, etc.)
- WHEN `POST /api/ai-results/report/` is called
- THEN the backend SHALL return `{"code": 400, "message": "<validation error details>"}`

#### Scenario: AI service reports results via BackendClient — [Status: Implemented]

- GIVEN the AI service `FrameProcessor` has built an AI report payload
- WHEN `BackendClient.report_ai_results(payload)` is called
- THEN it SHALL POST the payload to `{BACKEND_API_BASE_URL}/ai-results/report/`
- AND SHALL raise an HTTPError on non-2xx responses
- AND the HTTP request SHALL use a timeout of `BACKEND_TIMEOUT_SECONDS` (default `5` seconds)

#### Scenario: System health check — [Status: Implemented]

- GIVEN the backend is running
- WHEN `GET /api/health/` is called
- THEN the response SHALL return service status information

#### Scenario: AI results module placeholder — [Status: Implemented]

- GIVEN the backend is running
- WHEN `GET /api/ai-results/` is called
- THEN the response SHALL return `{"code": 200, "data": {"module": "ai_results", "status": "placeholder"}}`

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for AI Results Reporting in the Factory Vision system.


## AI Result Types (Produced by AI Service)

The `results` list in the report payload may contain the following detection types:

| Type | Produced By | Key Fields |
|------|------------|------------|
| `PERSON_DETECTION` | `PersonDetector` | `trackId`, `bbox`, `centerPoint`, `footPoint`, `confidence` |
| `FACE_RESULT` | `FaceRecognitionService` | `trackId`, `employeeId`, `employeeNo`, `employeeName`, `similarity`, `bbox` |
| `FALL_ALERT` | `FallDetector` | `trackId`, `isFall`, `ratio` |
| `RUNNING_ALERT` | `RunningDetector` | `trackId`, `isRunning`, `speed` |
| `ZONE_WARNING` | `ZoneDetector` | `trackId`, `zoneId`, `isInside`, `distance` |
| `HELMET_WARNING` | `HelmetDetector` (placeholder) | `trackId`, `helmetStatus`, `confidence` |

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for AI Results Reporting in the Factory Vision system.


## Planned Features (Not Yet Implemented)

- [ ] **Persist AI results:** No database models exist for storing detection events or alerts
- [ ] **Event/alert aggregation:** The report endpoint returns empty `eventIds` and `alertIds` arrays
- [ ] **Frontend real-time display:** `MonitorView.vue` uses hardcoded placeholder events, not live AI results

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for AI Results Reporting in the Factory Vision system.


## Constraints

- The AI service SHALL NOT write to the database directly — it SHALL always POST to `/api/ai-results/report/`.
- The backend currently accepts and validates reports but does not persist them — models.py is empty.
- Report payloads are synchronous HTTP POST requests. No message queue or async processing is used.

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for AI Results Reporting in the Factory Vision system.


## 变更说明

| 说明 |
|------|
| 全新 spec，基于 `backend/apps/ai_results/views.py`, `serializers.py`, `urls.py`, `tests.py` (2 tests) |
| 基于 `ai-service/modules/backend_client.py` L63-73 (`report_ai_results()` 方法) |
| 基于 `ai-service/modules/abnormal_behavior_service.py` 中的 payload 构建逻辑 |
| Result types 表基于 5 个 detector 的输出格式总结 |
