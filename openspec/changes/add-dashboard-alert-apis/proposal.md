# Change: Add dashboard and alert APIs

## Why

Dashboard and alert frontend pages still depend on placeholder data even though formal `Event` and `Alert` models are available. The backend needs stable read and status-update APIs before those pages can safely move to live data.

## What Changes

- Add paginated alert list and alert status handling APIs backed by `Alert` and its formal `Event` relation.
- Add a database-backed dashboard summary API with operational counts, recent alerts, and today's hourly event trend.
- Document the new API contracts and add endpoint tests.

## Affected Specs

- `event-alert`
- `dashboard`

## Non-Goals

- Do not modify frontend pages or remove placeholder data in this change.
- Do not add models, migrations, attendance data, or AIEvent compatibility.

## Acceptance

- Alert list supports pagination and severity, status, and camera filters.
- Alert handling updates only fields that exist on `Alert`.
- Dashboard values are computed from Camera, Employee, Event, and Alert records.
