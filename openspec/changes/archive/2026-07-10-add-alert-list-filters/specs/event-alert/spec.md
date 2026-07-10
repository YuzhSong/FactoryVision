## MODIFIED Requirements

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

