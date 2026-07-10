## ADDED Requirements

### Requirement: Reproducible local development data

The system SHALL use `backend/db.sqlite3` as its default local development database and SHALL provide reproducible demo data through a management command.

#### Scenario: Initialize local development data

- GIVEN the backend database has been migrated
- WHEN `python manage.py seed_dev_data` is run
- THEN the command SHALL idempotently create a development administrator, cameras, employees, zones, formal `Event` records, and `Alert` records
- AND every seeded alert SHALL reference a formal `Event`
- AND the command SHALL NOT create `AIEvent` data

#### Scenario: Exclude run logs from development data

- GIVEN a developer initializes a local database
- WHEN they follow the documented workflow
- THEN `.codex-runlogs/*.sqlite3` SHALL NOT be used as a daily development database or seed source
