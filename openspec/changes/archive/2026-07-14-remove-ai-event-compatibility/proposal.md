# Change: Remove AIEvent compatibility

## Why

The prior transition established `events.Event` as the formal event model but retained `AIEvent` and dual writes. The compatibility period is now complete. Keeping two event tables creates ambiguous ownership and lets local test artifacts become an accidental data source.

## What Changes

- Remove `AIEvent` and its persistence, admin, serializer, tests, and response fields.
- Make `Alert.event` the only alert-to-event relation and point it directly to `events.Event`.
- Make `POST /api/ai-results/report/` write only `events.Event` and optional `Alert` records.
- Provide a minimal formal event list endpoint at `GET /api/events/list/`.
- Add idempotent local development seed data for the default `backend/db.sqlite3` database.
- Document that `.codex-runlogs/*.sqlite3` is not a development database source.

## Affected Specs

- `ai-results`
- `event-alert`
- `local-development-data`

## Non-Goals

- Do not change the AI service report payload or production database configuration.
- Do not refactor frontend placeholder-backed pages in this change.
- Do not treat historical `.codex-runlogs` data as formal development data.

## Acceptance

- `Event` is the only persisted event model.
- `Alert.event` directly references `Event`, and no `system_event` field remains.
- AI report responses contain `eventIds` and optional `alertIds`, never AIEvent identifiers.
- `migrate` followed by `seed_dev_data` creates repeatable local demo data without AIEvent rows.
