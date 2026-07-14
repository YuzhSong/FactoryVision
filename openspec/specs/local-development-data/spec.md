# Local Development Data

## Purpose

Defines reproducible local database initialization without depending on captured runtime data.

## Requirements

### Requirement: Reproducible local development data

Backend SHALL provide idempotent seed data for the default local SQLite database.

#### Scenario: Initialize demo data

- **GIVEN** Backend migrations are applied
- **WHEN** `backend/.venv/Scripts/python.exe backend/manage.py seed_dev_data` is run
- **THEN** it SHALL idempotently create development users, cameras, employees, zones, formal Events, and Alerts
- **AND** every Alert SHALL reference a formal Event
- **AND** no AIEvent data SHALL be created

#### Scenario: Keep runtime databases separate

- **GIVEN** local development data is initialized
- **WHEN** repository runtime logs are present
- **THEN** `.codex-runlogs/*.sqlite3` SHALL NOT be used as the development database or seed source
