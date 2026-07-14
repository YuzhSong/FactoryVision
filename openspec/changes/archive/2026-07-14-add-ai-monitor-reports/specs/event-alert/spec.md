## ADDED Requirements

### Requirement: AI monitor report generation

The system SHALL persist one AI monitor report per report date.

#### Scenario: List monitor reports

- GIVEN MonitorReport records may exist
- WHEN `GET /api/reports/list/` is called by an authenticated user
- THEN the response SHALL include paginated report items
- AND each item SHALL include reportDate, alertCount, highAlertCount, pendingAlertCount, status, aiSummary, generatedAt, and documentPath
- AND the list SHALL NOT expose per-camera grouping

#### Scenario: Generate one daily report

- GIVEN Alert records may exist across multiple cameras
- WHEN the daily report task runs for a report date
- THEN it SHALL query alerts from the previous day at 12:00 to the report date at 12:00 local time
- AND it SHALL summarize all matching camera alerts into one MonitorReport
- AND it SHALL write a Word document under the reports media directory
- AND it SHALL upsert the report for that report date

#### Scenario: Manually generate a daily report

- GIVEN an authenticated user needs to generate or regenerate a report
- WHEN `POST /api/reports/generate/` is called with an optional reportDate
- THEN the system SHALL generate one report for that report date
- AND the response SHALL include the generated report detail
- AND future report dates SHALL be rejected
- AND when the reportDate is today, the period end SHALL be the current time instead of noon

#### Scenario: Preview a monitor report

- GIVEN a report id returned from the report list
- WHEN `GET /api/reports/{reportId}/` is called by an authenticated user
- THEN the response SHALL include report metadata, AI summary, generated text content, and alert details

#### Scenario: Download a monitor report

- GIVEN a report id returned from the report list
- WHEN `GET /api/reports/{reportId}/download/` is called by an authenticated user
- THEN the system SHALL return the generated Word document when it exists
