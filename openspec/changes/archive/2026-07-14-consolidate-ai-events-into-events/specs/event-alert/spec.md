## MODIFIED Requirements

### Requirement: Reserve Event Alert Center

The system SHALL include a dedicated event alert module for abnormal event and alarm handling workflows. The module SHALL own the formal event record used by AI result reporting.

#### Scenario: Persist formal AI event

- GIVEN AIService reports a valid detection result through `/api/ai-results/report/`
- WHEN the backend accepts the result
- THEN the backend SHALL persist a formal `events.Event`
- AND the event SHALL record camera, event type, source, severity, status, occurrence time, frame id, track id, bbox, confidence, snapshot path, and raw payload when available

#### Scenario: Create alert from formal event

- GIVEN AIService reports an alert-class result through `/api/ai-results/report/`
- WHEN the backend accepts the result
- THEN the backend SHALL create an `Alert`
- AND the alert SHALL retain compatibility with existing `AIEvent` linkage
- AND the alert SHALL also reference the formal `events.Event`
