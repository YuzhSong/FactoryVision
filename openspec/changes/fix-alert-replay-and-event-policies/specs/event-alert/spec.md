## MODIFIED Requirements

### Requirement: Alert detail shall expose replay-ready event evidence

`GET /api/alerts/{id}/detail/` SHALL return alert metadata, linked event metadata, and replay evidence suitable for a detail drawer.

#### Scenario: Display uploaded replay media without trajectory sketch

- **GIVEN** the alert detail response contains replay evidence
- **WHEN** the detail drawer is open
- **THEN** the frontend SHALL display the keyframe image when available
- **AND** SHALL display a playable video element when `clipUrl` is available
- **AND** SHALL display media paths and the raw event payload log
- **AND** SHALL NOT render a standalone trajectory sketch card

### Requirement: DingTalk escalation shall respect alert severity

DingTalk notifications SHALL notify the responsible person for alert-triggering events and SHALL only escalate high-risk alerts.

#### Scenario: Medium alert does not schedule escalation

- **GIVEN** an alert has `level=medium`
- **WHEN** the backend sends the initial DingTalk alert notification
- **THEN** the responsible person SHALL be notified
- **AND** no escalation timer SHALL be scheduled

#### Scenario: High alert can escalate

- **GIVEN** an alert has `level=high`
- **WHEN** the backend sends the initial DingTalk alert notification
- **THEN** the responsible person SHALL be notified
- **AND** an escalation timer SHALL be scheduled when escalation is enabled
