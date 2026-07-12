# Production Configuration & Security

> **Status:** 新建 —— 当前仅有开发默认值，生产部署安全需求待实施

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Production Configuration & Security in the Factory Vision system.


## Requirements

### Requirement: Production-Ready Security Configuration

The system SHALL enforce security-hardened configuration when deployed to any non-development environment. All security-sensitive settings SHALL be driven by environment variables with NO insecure defaults.

#### Scenario: Django SECRET_KEY in production — [Status: NOT Implemented — Critical Risk]

- GIVEN the backend is deployed to production
- WHEN `DJANGO_SECRET_KEY` environment variable is not set
- THEN the current default `"dev-secret-key"` SHALL NOT be used — **MUST be replaced with a required-no-default pattern**
- AND the deployment SHALL fail or refuse to start if the key is not provided

#### Scenario: DEBUG mode in production — [Status: NOT Implemented — Critical Risk]

- GIVEN the backend is deployed to production
- WHEN `DJANGO_DEBUG` environment variable is not set
- THEN the default SHALL be `False` (currently defaults to `"True"`)
- AND `DEBUG=True` SHALL never be allowed in production

#### Scenario: CORS policy in production — [Status: NOT Implemented — Critical Risk]

- GIVEN the backend is deployed to production
- THEN `CORS_ALLOW_ALL_ORIGINS` SHALL be `False` (currently hardcoded to `True`)
- AND `CORS_ALLOWED_ORIGINS` SHALL be set to the specific frontend origin via environment variable

#### Scenario: ALLOWED_HOSTS in production — [Status: Partial]

- GIVEN the backend is deployed to production
- WHEN `DJANGO_ALLOWED_HOSTS` is set
- THEN the backend SHALL only accept requests from those hostnames
- **Current state:** Default `"127.0.0.1,localhost"` is acceptable for dev but must be overridden in production

#### Scenario: Database configuration in production — [Status: Planned]

- GIVEN the backend is deployed to production
- WHEN `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` are set
- THEN the backend SHALL connect to the specified MySQL database (not SQLite)
- **Current state:** Defaults to SQLite at `BASE_DIR/db.sqlite3`

#### Scenario: HTTPS enforcement — [Status: NOT Implemented]

- GIVEN the backend is deployed to production
- THEN `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` SHALL be configured
- **Current state:** None of these settings are present in `settings.py`

#### Scenario: Docker-based production deployment — [Status: Planned]

- GIVEN all services have Dockerfiles and `docker-compose.prod.yml` is created
- WHEN `docker compose -f docker-compose.prod.yml up -d` is executed
- THEN the backend SHALL run via gunicorn (not `runserver`)
- AND the frontend SHALL be served via nginx (not `vite dev`)
- AND the AI service SHALL run via uvicorn without `--reload`
- AND all security environment variables SHALL be injected via Docker secrets or env file

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Production Configuration & Security in the Factory Vision system.


## Required Production Environment Variables

| Variable | Current Default | Production Requirement |
|----------|----------------|----------------------|
| `DJANGO_SECRET_KEY` | `"dev-secret-key"` | **Must be set** (no default, fail if absent) |
| `DJANGO_DEBUG` | `"True"` | **Must be** `"False"` |
| `DJANGO_ALLOWED_HOSTS` | `"127.0.0.1,localhost"` | **Must be set** to actual domain(s) |
| `CORS_ALLOWED_ORIGINS` | (not used, `CORS_ALLOW_ALL_ORIGINS=True`) | **Must be set** to frontend origin |
| `DB_ENGINE` | `"django.db.backends.sqlite3"` | `"django.db.backends.mysql"` |
| `DB_NAME` | `db.sqlite3` | Production database name |
| `DB_USER` | `""` | Production database user |
| `DB_PASSWORD` | `""` | Production database password |
| `DB_HOST` | `""` | Production database host |
| `DB_PORT` | `""` | `"3306"` |

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Production Configuration & Security in the Factory Vision system.


## Constraints

- No `.env` autoloading is configured (no `python-dotenv`) — environment variables must be set externally (shell, Docker, Jenkins).
- The Jenkinsfile currently has no `environment {}` block and no `credentials()` bindings — secrets are not injected during CI.
- No secrets management solution (Vault, AWS Secrets Manager, etc.) is configured.
- No settings file split exists (e.g., `settings/base.py` + `settings/production.py`) — a single `config/settings.py` serves all environments.

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Production Configuration & Security in the Factory Vision system.


## 变更说明

| 说明 |
|------|
| 全新 spec，基于 `backend/config/settings.py` 中所有 `os.getenv()` 调用的默认值分析 |
| 基于 `Jenkinsfile` Stages 7-8 中列出的生产部署前提条件 |
| 基于 Django 生产安全最佳实践（`SECURE_SSL_REDIRECT` 等缺失项） |
| 环境变量要求表基于代码实际行为（非猜测） |
