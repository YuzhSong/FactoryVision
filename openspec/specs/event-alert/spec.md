# Event Alert

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Event Alert in the Factory Vision system.
## Requirements
### Requirement: Alert list query

The alert list endpoint SHALL support keyword search on title and time-range filtering on occurred_at.

#### Scenario: Search alerts by keyword

- **GIVEN** the user is authenticated and alerts exist with titles like "危险区域入侵"
- **WHEN** `GET /api/alerts/list/?keyword=区域&page=1&pageSize=20` is called
- **THEN** the backend SHALL return alerts whose `title` contains the keyword (case-insensitive)
- **AND** SHALL support Chinese characters in keyword

#### Scenario: Filter alerts by time range

- **GIVEN** alerts exist with occurred_at timestamps
- **WHEN** `GET /api/alerts/list/?startTime=2026-07-10T00:00:00&endTime=2026-07-10T23:59:59` is called
- **THEN** the backend SHALL return only alerts whose occurred_at falls within the specified range
- **AND** omitting startTime or endTime SHALL not apply the respective boundary

#### Scenario: Combined filter

- **GIVEN** the user applies keyword, severity, status, and time range filters simultaneously
- **WHEN** `GET /api/alerts/list/?keyword=入侵&severity=high&status=pending&startTime=...&endTime=...` is called
- **THEN** all conditions SHALL be combined with logical AND

### Requirement: Alert handling

The alert center SHALL allow security personnel to change alert status through a dedicated endpoint.

#### Scenario: Handle an alert

- **GIVEN** the user is authenticated and alert id=1 exists
- **WHEN** `POST /api/alerts/1/handle/` is called with `{status:"processing"}`
- **THEN** the alert status SHALL be updated and the full alert object returned

#### Scenario: Alert not found

- **GIVEN** alert id=999 does not exist
- **WHEN** `POST /api/alerts/999/handle/` is called
- **THEN** the backend SHALL return HTTP 404 with message "告警不存在"

### Requirement: Chinese Swagger documentation

All alert endpoints SHALL display Chinese descriptions and response examples in the Swagger UI.

#### Scenario: Swagger in Chinese

- **GIVEN** the backend is running
- **WHEN** the developer opens `/api/docs/`
- **THEN** alert endpoints SHALL show Chinese summaries, parameter descriptions, and response examples

## API Endpoints

| Method | URL | Description | Auth |
|--------|-----|-------------|------|
| `GET` | `/api/alerts/list/` | 告警列表（支持 keyword/severity/status/startTime/endTime/page/pageSize） | No |
| `POST` | `/api/alerts/{id}/handle/` | 处置告警（pending→processing→closed） | Bearer JWT |