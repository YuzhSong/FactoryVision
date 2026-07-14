## MODIFIED Requirements

### Requirement: AI Detection Result Reporting

The system SHALL provide a backend endpoint for the AI service to report detection results. The endpoint SHALL validate the payload structure, persist accepted results as formal events, and return acceptance confirmation.

#### Scenario: Report AI detection results

- GIVEN the AI service has processed a video frame and produced detection results
- WHEN `POST /api/ai-results/report/` is called with a valid JSON payload
- THEN the backend SHALL validate required fields:
  - `cameraId`: existing camera id or camera code
  - `frameId`: optional string
  - `timestamp`: valid ISO 8601 datetime string
  - `results`: list of result objects, which may be empty
- AND each result with a non-empty `type` SHALL create one formal `events.Event`
- AND the response SHALL include `acceptedResults`, `rejectedResults`, `eventIds`, `alertIds`, `cameraId`, and `frameId`
- AND `eventIds` SHALL contain ids from the formal `events.Event` table
- AND transitional `aiEventIds` MAY be returned while `AIEvent` compatibility writes are enabled

#### Scenario: Report person detection without alert

- GIVEN a valid payload contains one `PERSON_DETECTION` result
- WHEN `POST /api/ai-results/report/` is called
- THEN the backend SHALL create one formal `events.Event`
- AND the event SHALL preserve bbox, track id, confidence if present, frame id, camera, timestamp, and raw payload
- AND the backend SHALL NOT create an `Alert`

#### Scenario: Report alert-class AI result

- GIVEN a valid payload contains one alert-class result such as `ZONE_WARNING` or `HELMET_WARNING`
- WHEN `POST /api/ai-results/report/` is called
- THEN the backend SHALL create one formal `events.Event`
- AND the backend SHALL create one `Alert`
- AND the alert SHALL be traceable to the formal event
