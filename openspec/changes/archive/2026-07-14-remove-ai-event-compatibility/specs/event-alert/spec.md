## MODIFIED Requirements

### Requirement: Reserve Event Alert Center

The system SHALL include a dedicated event alert module for abnormal event and alarm handling workflows. `events.Event` SHALL be the only formal event record.

#### Scenario: Create alert from formal event

- GIVEN AIService reports an alert-class result through `/api/ai-results/report/`
- WHEN the backend accepts the result
- THEN the backend SHALL create an `Alert`
- AND `Alert.event` SHALL directly reference the resulting `events.Event`
- AND the alert SHALL NOT retain an AIEvent or `system_event` compatibility relation

#### Scenario: List formal events

- GIVEN formal events have been persisted
- WHEN `GET /api/events/list/` is called
- THEN the backend SHALL return records from `events.Event`
- AND the response SHALL NOT depend on `AIEvent`
