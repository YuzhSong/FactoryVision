# AI Results Reporting

> **Status:** Implemented — AI reports are converted into `Event` records and alert-type results create `Alert` records.

## Purpose

Defines how the AI service reports structured frame-level detection results to the Django backend, and how those results enter the event and alert pipeline.

## Requirements

### Requirement: AI Detection Result Reporting

The system SHALL provide a backend endpoint for the AI service to report detection results. The endpoint SHALL validate the payload, resolve the target camera, create formal event records, and create alert records for warning/alert result types.

#### Scenario: Report AI detection results — [Status: Implemented]

- GIVEN the AI service has processed a video frame and produced detection results
- WHEN `POST /api/ai-results/report/` is called with a valid JSON payload
- THEN the backend SHALL validate required fields:
  - `cameraId`: camera numeric ID or camera code string
  - `frameId`: optional string, defaults to empty string
  - `timestamp`: valid ISO 8601 datetime string
  - `results`: list of result objects, may be empty
  - `eventMedia`: optional list of media metadata objects
- AND the backend SHALL resolve `cameraId` by `Camera.id` first when numeric, otherwise by `Camera.code`
- AND each result object with a non-empty `type` SHALL create one `events.Event` record
- AND the response SHALL include created event IDs, created alert IDs, accepted result count, rejected result count, camera ID, and frame ID.

#### Scenario: Create events from report results — [Status: Implemented]

- GIVEN a valid report contains result objects such as `PERSON_DETECTION`, `FACE_RESULT`, `HELMET_WARNING`, `ZONE_WARNING`, `FALL_ALERT`, or `RUNNING_ALERT`
- WHEN the report is accepted
- THEN each accepted result SHALL be stored as an `Event` with:
  - `camera`: resolved camera foreign key
  - `camera_identifier`: submitted `cameraId` as string
  - `frame_id`: submitted frame ID
  - `event_type`: result `type`
  - `source`: `ai_service`
  - `severity`: derived from explicit `level`, alert defaults, or `info`
  - `track_id`, `bbox`, `confidence`, `snapshot_path`, and raw `payload` extracted from the result
  - `occurred_at`: submitted timestamp

#### Scenario: Create alerts for warning and alert results — [Status: Implemented]

- GIVEN an accepted result type is in the alert set or ends with `_WARNING` / `_ALERT`
- WHEN the backend creates its corresponding `Event`
- THEN the backend SHALL create one `Alert` linked to that event
- AND the response `alertIds` SHALL contain the created alert ID
- AND alert status SHALL default to `pending`.

#### Scenario: Reject invalid AI report — [Status: Implemented]

- GIVEN an invalid payload, missing timestamp, malformed results, or an unresolved camera
- WHEN `POST /api/ai-results/report/` is called
- THEN the backend SHALL return HTTP 400 with `code=400` and validation details.

#### Scenario: AI service reports results via BackendClient — [Status: Implemented]

- GIVEN the AI service has built an AI report payload
- WHEN `BackendClient.report_ai_results(payload)` is called
- THEN it SHALL POST the payload to `{BACKEND_API_BASE_URL}/ai-results/report/`
- AND SHALL raise an HTTP error on non-2xx responses
- AND the request SHALL use `BACKEND_TIMEOUT_SECONDS`.

#### Scenario: AI service bootstrap data — [Status: Implemented]

- GIVEN the backend has cameras, zones, employees, and threshold configuration
- WHEN `GET /api/ai/bootstrap/` is called
- THEN the backend SHALL return cameras, zones, employees with face features, thresholds, and a timestamp for AI-service runtime cache initialization.

#### Scenario: System health check — [Status: Implemented]

- GIVEN the backend is running
- WHEN `GET /api/health/` is called
- THEN the response SHALL return service status information.

#### Scenario: AI results module placeholder — [Status: Implemented]

- GIVEN the backend is running
- WHEN `GET /api/ai-results/` is called
- THEN the response SHALL return module placeholder status.

## AI Result Types Produced by AI Service

| Type | Produced By | Key Fields |
|------|------------|------------|
| `PERSON_DETECTION` | `PersonDetector` | `trackId`, `bbox`, `centerPoint`, `footPoint`, `confidence` |
| `FACE_RESULT` | `FaceRecognitionService` | `trackId`, `employeeId`, `employeeNo`, `employeeName`, `similarity`, `bbox`, `matched` |
| `FALL_ALERT` | `FallDetector` | `trackId`, `isFall`, `ratio`, `level` |
| `RUNNING_ALERT` | `RunningDetector` | `trackId`, `isRunning`, `speed`, `level` |
| `ZONE_WARNING` | `ZoneDetector` | `trackId`, `zoneId`, `zoneName`, `isInside`, `distance`, `level` |
| `HELMET_WARNING` | `HelmetDetector` | `trackId`, `helmetStatus`, `confidence`, `level` |
| `STRANGER_ALERT` / `STRANGER_DETECTED` | `StrangerDetector` | `trackId`, `bbox`, `confidence`, `level` |
| `EMPLOYEE_ABSENT` / `EMPLOYEE_RETURNED` | `EmployeePresenceDetector` | `employeeId`, `employeeNo`, `employeeName`, `trackId` |

## Implemented Behavior

- AI reports are not stored in a separate `ai_result` table.
- Accepted results are normalized into the formal `events.Event` table.
- Warning/alert result types create `ai_results.Alert` records linked one-to-one with `Event`.
- WebSocket push is attempted for alert-level events and selected face-recognition events; push failures do not roll back event creation.
- The AI service must report through backend HTTP APIs and must not write the database directly.

## Constraints

- `cameraId` must resolve to an existing camera by numeric ID or camera code.
- Empty or missing result `type` values are rejected per item and counted in `rejectedResults`.
- Report handling is synchronous HTTP POST; no message queue is currently used.
- Backend event and alert persistence is the source of truth for reported AI results.

## Change Notes

| Description |
|-------------|
| Updated to match current `backend/apps/ai_results/views.py`, `models.py`, `serializers.py`, and `tests.py`. |
| Reflects consolidation of AI report persistence into `events.Event` plus `ai_results.Alert`. |
| Reflects `GET /api/ai/bootstrap/` used by AI-service runtime cache initialization. |
