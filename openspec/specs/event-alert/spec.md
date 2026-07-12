# Event Alert

## Purpose

Defines how formal events and alerts are created, queried, handled, summarized, and pushed to realtime clients.

## Requirements

### Requirement: Event records

The backend SHALL store formal event records generated from AI reports.

#### Scenario: Create event from AI result — [Status: Implemented]

- **GIVEN** `POST /api/ai-results/report/` receives a valid result item with non-empty `type`
- **WHEN** the report is accepted
- **THEN** one `events.Event` record SHALL be created
- **AND** it SHALL contain camera, source, severity, status, occurred time, frame ID, track ID, bbox, confidence, snapshot path, and raw payload.

#### Scenario: List formal events — [Status: Implemented]

- **GIVEN** event records exist
- **WHEN** `GET /api/events/list/` is called
- **THEN** the backend SHALL return formal `Event` records with total count and serialized items.

### Requirement: Alert creation from AI events

The backend SHALL create alert records for AI result types that represent warning or alert conditions.

#### Scenario: Create alert for warning result — [Status: Implemented]

- **GIVEN** an accepted AI result type is configured as an alert type, ends with `_WARNING`, or ends with `_ALERT`
- **WHEN** the corresponding event is created
- **THEN** one `Alert` record SHALL be created and linked to the event
- **AND** the alert status SHALL default to `pending`
- **AND** the AI report response SHALL include the alert ID in `alertIds`.

#### Scenario: Do not create alert for informational person detection — [Status: Implemented]

- **GIVEN** an accepted AI result type is `PERSON_DETECTION`
- **WHEN** the corresponding event is created
- **THEN** the backend SHALL persist the event
- **AND** it SHALL NOT create an alert by default.

### Requirement: Realtime event push

The backend SHALL attempt to push selected AI-created events to WebSocket clients subscribed to the camera.

#### Scenario: Push alert event to realtime channel — [Status: Implemented]

- **GIVEN** an accepted AI result creates an alert-level event
- **WHEN** the event is stored
- **THEN** the backend SHALL attempt to send an `EVENT_CREATED` message to `realtime_{cameraId}`
- **AND** WebSocket push failure SHALL NOT roll back event or alert creation.

#### Scenario: Deduplicate matched face push per track and employee — [Status: Implemented]

- **GIVEN** a report contains matched `FACE_RESULT` items with the same `trackId` and `employeeId`
- **WHEN** WebSocket push is evaluated
- **THEN** at most one push SHALL be emitted for that track/employee key within the report.

### Requirement: Alert list query

The alert list endpoint SHALL support pagination, keyword search, camera filtering, severity filtering, status filtering, and time-range filtering on `occurred_at`.

#### Scenario: Search alerts by keyword — [Status: Implemented]

- **GIVEN** alerts exist with titles like "危险区域入侵"
- **WHEN** `GET /api/alerts/list/?keyword=区域&page=1&pageSize=20` is called
- **THEN** the backend SHALL return alerts whose `title` contains the keyword case-insensitively
- **AND** SHALL support Chinese characters in keyword.

#### Scenario: Filter alerts by time range — [Status: Implemented]

- **GIVEN** alerts exist with occurred_at timestamps
- **WHEN** `GET /api/alerts/list/?startTime=2026-07-10T00:00:00&endTime=2026-07-10T23:59:59` is called
- **THEN** the backend SHALL return only alerts whose `occurred_at` falls within the specified range
- **AND** omitting startTime or endTime SHALL not apply the respective boundary.

#### Scenario: Combined filter — [Status: Implemented]

- **GIVEN** the user applies keyword, severity, status, camera ID, and time range filters simultaneously
- **WHEN** `GET /api/alerts/list/?keyword=入侵&severity=high&status=pending&cameraId=1&startTime=...&endTime=...` is called
- **THEN** all conditions SHALL be combined with logical AND.

#### Scenario: Reject invalid pagination or camera parameter — [Status: Implemented]

- **GIVEN** page, pageSize, or cameraId is invalid
- **WHEN** `GET /api/alerts/list/` is called
- **THEN** the backend SHALL return HTTP 400 with a validation message.

### Requirement: Alert handling

The alert center SHALL allow alert status updates through a dedicated endpoint.

#### Scenario: Handle an alert — [Status: Implemented]

- **GIVEN** alert id=1 exists
- **WHEN** `POST /api/alerts/1/handle/` is called with `{status:"processing"}`
- **THEN** the alert status SHALL be updated and the full alert object returned.

#### Scenario: Alert not found — [Status: Implemented]

- **GIVEN** alert id=999 does not exist
- **WHEN** `POST /api/alerts/999/handle/` is called
- **THEN** the backend SHALL return HTTP 404 with message "告警不存在".

### Requirement: Dashboard summary

The backend SHALL provide database-backed operational summary data for the dashboard.

#### Scenario: Query dashboard summary — [Status: Implemented]

- **GIVEN** cameras, employees, events, and alerts exist
- **WHEN** `GET /api/dashboard/summary/` is called
- **THEN** the backend SHALL return camera counts, employee count, today's event count, today's alert count, pending alert count, recent alerts, and today's hourly event trend.

### Requirement: Chinese Swagger documentation

All alert endpoints SHALL display Chinese descriptions and response examples in the Swagger UI.

#### Scenario: Swagger in Chinese — [Status: Implemented]

- **GIVEN** the backend is running
- **WHEN** the developer opens `/api/docs/`
- **THEN** alert endpoints SHALL show Chinese summaries, parameter descriptions, and response examples.

## API Endpoints

| Method | URL | Description | Auth |
|--------|-----|-------------|------|
| `GET` | `/api/events/list/` | 事件列表 | No |
| `GET` | `/api/alerts/list/` | 告警列表（支持 keyword/severity/status/cameraId/startTime/endTime/page/pageSize） | No |
| `POST` | `/api/alerts/{id}/handle/` | 处置告警状态 | Bearer JWT |
| `GET` | `/api/dashboard/summary/` | 看板统计摘要 | No |
| `WS` | `/ws/realtime/{cameraId}/` | 指定摄像头实时事件消息 | Token via query/header |
