## ADDED Requirements

### Requirement: Alert query and handling API

The system SHALL expose Alert records backed by the formal Event relation for alert center clients.

#### Scenario: List alerts

- GIVEN Alert records exist
- WHEN `GET /api/alerts/list/` is called
- THEN the backend SHALL return `{total, items}`
- AND each item SHALL include id, title, eventType, severity, status, cameraId, cameraName, occurredAt, and description
- AND the endpoint SHALL support positive `page` and `pageSize` parameters
- AND the endpoint SHALL support optional `severity`, `status`, and `cameraId` filters

#### Scenario: Handle alert

- GIVEN an Alert exists
- WHEN `POST /api/alerts/{id}/handle/` is called with a valid status
- THEN the backend SHALL update the Alert status
- AND the backend SHALL NOT create a new Event or any AIEvent data
- AND handler identity or handling time SHALL only be persisted when fields exist on the model
