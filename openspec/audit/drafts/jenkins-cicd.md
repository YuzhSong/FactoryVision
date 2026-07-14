# Jenkins CI/CD

> **Status:** ⚠️ 已更新 —— 从 4 个 placeholder stage 扩展为实际 8 个 stage（6 实 + 2 占位）

---

## Requirement: Jenkins Pipeline for CI/CD

The project SHALL provide a Jenkins Declarative Pipeline that covers code checkout, backend validation, backend testing, frontend building, AI service testing, artifact archiving, and reserved stages for Docker image building and deployment.

### Scenario: Checkout — [Status: Implemented]

- GIVEN a Jenkins job is triggered for the repository
- WHEN the pipeline executes Stage 1 (Checkout)
- THEN `checkout scm` SHALL pull the latest commit of the configured branch

### Scenario: Backend system check — [Status: Implemented]

- GIVEN the repository is checked out
- WHEN the pipeline executes Stage 2 (Backend Check)
- THEN it SHALL run `pip install -r requirements.txt` in the `backend/` directory
- AND SHALL run `python manage.py check` to validate Django configuration
- AND SHALL support both Unix (`sh`) and Windows (`bat`) agents

### Scenario: Backend unit tests — [Status: Implemented]

- GIVEN the backend system check passes
- WHEN the pipeline executes Stage 3 (Backend Test)
- THEN it SHALL run `python manage.py test --verbosity=2` in the `backend/` directory

### Scenario: Frontend production build — [Status: Implemented]

- GIVEN the repository is checked out
- WHEN the pipeline executes Stage 4 (Frontend Build)
- THEN it SHALL run `npm install` followed by `npm run build` in the `frontend/` directory
- AND the build artifacts SHALL be produced at `frontend/dist/`
- NOTE: `npm lint` and `npm test` are NOT executed because they are not yet configured in `package.json`

### Scenario: AI service unit tests — [Status: Implemented]

- GIVEN the repository is checked out
- WHEN the pipeline executes Stage 5 (AI Service Test)
- THEN it SHALL run `pip install -r requirements.txt` in the `ai-service/` directory
- AND SHALL run `python -m unittest discover tests` to execute all AI service test cases

### Scenario: Archive frontend build artifacts — [Status: Implemented]

- GIVEN the frontend build completes
- WHEN the pipeline executes Stage 6 (Archive Artifacts)
- THEN it SHALL archive `frontend/dist/**` using `archiveArtifacts` with fingerprinting enabled
- AND archive failure SHALL NOT fail the pipeline (try-catch protected)

### Scenario: Docker image building — [Status: Planned / Placeholder]

- GIVEN the previous stages have all passed
- WHEN the pipeline executes Stage 7 (Docker Build)
- THEN it SHALL currently output informational messages listing prerequisites
- AND it SHALL NOT execute any `docker build` commands
- **Prerequisites for activation:**
  1. `backend/Dockerfile` — python:3.14-slim + gunicorn
  2. `frontend/Dockerfile` — multi-stage: node build + nginx static serving
  3. `ai-service/Dockerfile` — python:3.14-slim + uvicorn (without --reload)
  4. `docker-compose.prod.yml` — production compose configuration

### Scenario: Deploy to test environment — [Status: Planned / Placeholder]

- GIVEN Docker images have been built
- WHEN the pipeline executes Stage 8 (Deploy Test Environment)
- THEN it SHALL currently output informational messages listing prerequisites
- AND it SHALL NOT execute any deployment commands
- **Prerequisites for activation:**
  1. `docker-compose.prod.yml` with pre-built images, nginx for frontend, gunicorn for backend
  2. Production environment variables: `DJANGO_DEBUG=False`, `DB_ENGINE=mysql`, DB credentials
  3. Deployment command: `docker compose -f docker-compose.prod.yml up -d`

---

## Pipeline Post Actions — [Status: Implemented]

- On `always`: Output pipeline completion summary
- On `success`: Output "✓ 所有阶段执行成功！"
- On `failure`: Output "✗ 部分阶段执行失败，请查看上方日志定位问题"

---

## Constraints

- The pipeline uses `agent any` and supports both Unix (`sh`) and Windows (`bat`) agents.
- No Jenkins `environment {}` block is configured — environment variables (e.g., `DJANGO_SECRET_KEY`) are not injected.
- No `credentials()` bindings are used.
- No virtual environment is created — `pip install` runs against the system Python.
- No `python manage.py migrate` step exists in the pipeline.

---

## 变更说明

| 变更 | 原 spec | 新草稿 | 依据 |
|------|---------|--------|------|
| Stage 数量 | 4 | 8（6 实 + 2 占位） | `Jenkinsfile` L10-235 |
| Stage 描述 | 全部为 "placeholder" | 逐一区分 Implemented/Planned | 逐 stage 分析命令 |
| 新增 Backend Test | 无 | Stage 3: `manage.py test` | `Jenkinsfile` L57-75 |
| 新增 AI Service Test | 无 | Stage 5: `unittest discover` | `Jenkinsfile` L115-138 |
| 新增 Archive Artifacts | 无 | Stage 6: `archiveArtifacts` | `Jenkinsfile` L143-165 |
| 新增 Docker Build（占位） | 无 | Stage 7: 仅 echo，列出前提条件 | `Jenkinsfile` L167-201 |
| 新增 Deploy（占位） | 无 | Stage 8: 仅 echo，列出前提条件 | `Jenkinsfile` L203-235 |
| Frontend Build 限制 | 无 | 补充 "不运行 lint/test" 注释 | `Jenkinsfile` L80 注释 |
| 新增 Constraints | 无 | agent any, 无 env block, 无 migrate | `Jenkinsfile` 分析 |
