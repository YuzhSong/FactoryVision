# Change: Add AI monitor report page and APIs

## Why

The project needs an optional AI workflow feature that can produce daily monitoring reports from alert events. Users need a frontend page to browse generated reports, preview report content, and download a document.

## What Changes

- Replace the frontend attendance navigation entry with an AI monitor report page.
- Add report list, detail preview, and download API endpoints under `/api/reports/`.
- Persist one daily report per report date in a MonitorReport table.
- Generate each daily report from all camera alerts in the previous day 12:00 to current day 12:00 period.
- Use APScheduler to run daily generation at 12:00.
- Use DeepSeek through an environment-provided API key to summarize alert events.
- Write the generated report to a Word document under `media/reports/`.

## Affected Specs

- `event-alert`
- `api-conventions`

## Non-Goals

- Do not remove the existing attendance backend placeholder.
- Do not commit real AI API keys.
- Do not create per-camera reports in this change.
- Do not change existing alert, event, camera, employee, monitor, or zone API contracts.

## Acceptance

- `/reports` renders inside the existing Vue + Element Plus workbench layout.
- Users can view one report per day, preview its generated text, and download its Word document.
- Backend report APIs follow the project response envelope for JSON endpoints.
- The implementation does not change existing alert, camera, employee, monitor, or zone API contracts.
