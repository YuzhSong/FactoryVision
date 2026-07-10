# Local Development Database

The default local development database is `backend/db.sqlite3`. It is ignored by Git and is recreated from migrations and seed data; do not commit SQLite database files.

## Initialize

```powershell
cd backend
python manage.py migrate
python manage.py seed_dev_data
python manage.py runserver
```

`seed_dev_data` is idempotent. It creates the `admin` user with password `admin123456`, two cameras, three employees, two zones, eight formal events, and five alerts.

## Reset

Stop the backend, delete `backend/db.sqlite3`, then run `migrate` and `seed_dev_data` again.

## Boundaries

- Do not use `.codex-runlogs/*.sqlite3` as a daily development database or seed source.
- The AIEvent compatibility period has ended. `Event` is the formal event model, `Alert.event` directly references it, and `/api/ai-results/report/` writes only `Event` plus optional `Alert` rows.
- `seed_dev_data` does not generate AIEvent data.
- `frontend/src/data/placeholders.js` remains in the repository. This phase does not refactor the dashboard, monitor, alert, or attendance pages that still use it.
