## ADDED Requirements

### Requirement: Realtime event WebSocket

The system SHALL provide a WebSocket endpoint that pushes AI detection events to connected frontend clients in real time, scoped by camera ID.

#### Scenario: Connect to camera realtime feed

- **GIVEN** the user selects a camera in the monitor page
- **WHEN** the frontend establishes a WebSocket connection to `/ws/realtime/{cameraId}/`
- **THEN** the backend SHALL accept the connection
- **AND** the frontend SHALL receive new detection events as JSON messages

#### Scenario: Event push on AI report

- **GIVEN** a WebSocket client is connected for cameraId=1
- **WHEN** AI Service reports detection results for cameraId=1 via `POST /api/ai-results/report/`
- **THEN** the backend SHALL create the Event record
- **AND** SHALL push the new event to all WebSocket clients connected to cameraId=1

#### Scenario: Camera switch disconnects

- **GIVEN** a WebSocket connection is open for cameraId=1
- **WHEN** the user switches to cameraId=2
- **THEN** the frontend SHALL close the WebSocket connection for cameraId=1
- **AND** establish a new connection for cameraId=2

#### Scenario: Message format

- **GIVEN** a new event is pushed via WebSocket
- **THEN** the message SHALL include: `{type, cameraId, timestamp, payload:{eventId, eventType, severity, trackId, bbox, confidence, occurredAt}}`

### Requirement: WebSocket infrastructure

The backend SHALL use Django Channels with an in-memory channel layer for development.

#### Scenario: ASGI configuration

- **GIVEN** the project uses Channels
- **WHEN** the server starts
- **THEN** the ASGI application SHALL route HTTP and WebSocket requests correctly
- **AND** the in-memory channel layer SHALL be used for local development
