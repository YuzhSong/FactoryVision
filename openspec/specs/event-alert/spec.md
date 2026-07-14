# Event and Alert

## Purpose

Defines formal event persistence, alert query/handling, realtime delivery, replay presentation, notification policy, and AI monitor reports.

## Requirements

### Requirement: Formal event ownership

`events.Event` SHALL be the only formal event record.

#### Scenario: Persist reported result

- **GIVEN** Backend accepts an AI result
- **WHEN** persistence completes
- **THEN** an `Event` SHALL record camera, type, source, severity, status, occurrence time, frame, track, bbox, confidence, snapshot, and payload when available
- **AND** alert-class results SHALL create an `Alert` linked through `Alert.event`
- **AND** no AIEvent compatibility relation SHALL be created or returned

#### Scenario: List formal events

- **GIVEN** events exist
- **WHEN** `GET /api/events/list/` is called
- **THEN** records SHALL come from `events.Event`

### Requirement: Alert query and handling

Backend SHALL provide filterable alert queries and validated status transitions.

#### Scenario: List and filter alerts

- **GIVEN** alerts exist
- **WHEN** `GET /api/alerts/list/` is called
- **THEN** Backend SHALL return paginated alert items
- **AND** SHALL support keyword, severity, status, camera, and occurrence-time filters combined with logical AND

#### Scenario: Handle alert

- **GIVEN** an Alert exists
- **WHEN** `POST /api/alerts/{id}/handle/` receives a valid next status
- **THEN** Backend SHALL update and return the Alert
- **AND** invalid transitions or missing alerts SHALL return clear errors

### Requirement: Realtime event WebSocket

Backend SHALL push new events to camera-scoped WebSocket clients through Django Channels.

#### Scenario: Receive camera event

- **GIVEN** a client is connected to `/ws/realtime/{cameraId}/`
- **WHEN** AIService reports an event for that camera
- **THEN** the client SHALL receive JSON containing event type, camera, timestamp, event id, severity, track, bbox, confidence, and occurrence time

#### Scenario: Switch camera

- **GIVEN** the monitor is connected to one camera
- **WHEN** the selected camera changes or the page closes
- **THEN** Frontend SHALL close the old socket before opening another

### Requirement: Alert detail shall expose replay-ready evidence

Backend SHALL return replay-ready evidence and Frontend SHALL present available media safely.

#### Scenario: Return alert detail

- **GIVEN** an Alert is linked to an Event
- **WHEN** `GET /api/alerts/{id}/detail/` is called
- **THEN** the response SHALL include alert, event, trajectory/trigger/region context, raw payload, and media URLs
- **AND** missing evidence SHALL use null or empty values rather than failing

#### Scenario: Present evidence

- **GIVEN** detail contains a keyframe or clip URL
- **WHEN** the drawer opens
- **THEN** Frontend SHALL show the image and/or playable video
- **AND** SHALL show media paths and event payload data
- **AND** SHALL NOT render the retired standalone trajectory sketch card

### Requirement: DingTalk escalation shall respect alert severity

Notification escalation SHALL depend on alert severity and deployment configuration.

#### Scenario: Medium alert

- **GIVEN** an alert is medium severity
- **WHEN** the initial notification is sent
- **THEN** the responsible person SHALL be notified
- **AND** no escalation timer SHALL be scheduled

#### Scenario: High alert

- **GIVEN** an alert is high severity and escalation is enabled
- **WHEN** the initial notification is sent
- **THEN** an escalation timer MAY be scheduled

### Requirement: AI monitor report generation

Backend SHALL generate, persist, preview, and download period-based AI monitor reports.

#### Scenario: Generate report period

- **GIVEN** alerts exist in a requested six-hour period
- **WHEN** a scheduled or manual generation runs
- **THEN** Backend SHALL upsert one `MonitorReport` for that exact period
- **AND** SHALL generate plain text, keyframe-aware preview data, and a valid Word document
- **AND** future periods SHALL be rejected

#### Scenario: List, preview, and download

- **GIVEN** a report exists
- **WHEN** an authenticated user calls report list, detail, or download endpoints
- **THEN** Backend SHALL return the matching metadata/content or DOCX file
- **AND** the downloaded file SHALL preserve Chinese text and embedded images when available
