## ADDED Requirements

### Requirement: Alert detail replay evidence

The alert center SHALL provide a detail endpoint for one alert that returns the alert record, the linked event record, and replay evidence needed by the frontend.

#### Scenario: Get alert replay detail

- **GIVEN** an alert exists and is linked to a formal `Event`
- **WHEN** `GET /api/alerts/{id}/detail/` is called
- **THEN** the backend SHALL return the alert summary fields
- **AND** SHALL return linked event fields including `eventId`, `eventType`, `cameraId`, `cameraName`, `occurredAt`, `trackId`, `bbox`, `confidence`, and `payload`
- **AND** SHALL return a `replay` object containing `trajectory`, `triggerPoint`, `region`, and `media` keys
- **AND** missing replay evidence SHALL be represented by empty arrays or `null` values rather than causing an error

#### Scenario: Alert detail not found

- **GIVEN** alert id=999 does not exist
- **WHEN** `GET /api/alerts/999/detail/` is called
- **THEN** the backend SHALL return HTTP 404 with a clear not-found message

### Requirement: Alert center replay presentation

The frontend alert center SHALL display replay evidence when the user opens alert details.

#### Scenario: Show available trajectory

- **GIVEN** the alert detail response contains replay trajectory points
- **WHEN** the user clicks "查看" in the alert center
- **THEN** the detail drawer SHALL show the alert log and a visual trajectory preview
- **AND** the trajectory preview SHALL draw available region context, bbox, path line, and trigger point when present

#### Scenario: Replay evidence absent

- **GIVEN** the alert detail response has no trajectory or media
- **WHEN** the user opens the alert detail drawer
- **THEN** the frontend SHALL still show alert and event logs
- **AND** SHALL show an empty-state message for replay evidence instead of failing

