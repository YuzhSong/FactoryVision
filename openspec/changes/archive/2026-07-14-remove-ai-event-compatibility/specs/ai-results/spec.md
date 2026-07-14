## MODIFIED Requirements

### Requirement: AI Detection Result Reporting

The system SHALL provide a backend endpoint for the AI service to report detection results. The endpoint SHALL validate the payload structure, persist accepted results only as formal `events.Event` records, and return acceptance confirmation.

#### Scenario: Report AI detection results

- GIVEN the AI service has processed a video frame and produced detection results
- WHEN `POST /api/ai-results/report/` is called with a valid JSON payload
- THEN each result with a non-empty `type` SHALL create one `events.Event`
- AND alert-class results SHALL create one `Alert` linked through `Alert.event`
- AND the response SHALL include `acceptedResults`, `rejectedResults`, `eventIds`, `alertIds`, `cameraId`, and `frameId`
- AND the response SHALL NOT include AIEvent identifiers

#### Scenario: End AIEvent compatibility

- GIVEN the AI event report endpoint accepts a result
- WHEN persistence completes
- THEN the backend SHALL NOT create, query, or return `AIEvent` data
