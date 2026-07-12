# Authentication & Authorization

> **Status:** 新建 —— 基于已实现的代码

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Authentication & Authorization in the Factory Vision system.


## Requirements

### Requirement: JWT-Based Authentication

The system SHALL provide JSON Web Token (JWT) based authentication for frontend-to-backend API access. Users SHALL be authenticated via username/password and receive a time-limited access token.

#### Scenario: User login — [Status: Implemented]

- GIVEN a registered user with username and password
- WHEN `POST /api/auth/login/` is called with `{"username": "<username>", "password": "<password>"}`
- **Note:** The login form's username field defaults to `'admin'` in the frontend (`LoginView.vue:12`)
- THEN the backend SHALL authenticate against Django's auth system
- AND upon success SHALL return `{"code": 200, "data": {"token": "<JWT access token>", "user": {"id": <int>, "username": "<str>", "role": "<admin|operator>"}}}`
- AND upon failure SHALL return `{"code": 401, "message": "账号或密码错误"}`
- AND if the account is disabled, SHALL return `{"code": 403, "message": "账号已被禁用"}`
- AND the JWT access token SHALL expire after 24 hours

#### Scenario: Token-based authenticated requests — [Status: Implemented]

- GIVEN a valid JWT access token stored in `localStorage` as `factoryVisionToken`
- WHEN any authenticated API request is made
- THEN the frontend Axios interceptor SHALL attach `Authorization: Bearer <token>` header
- AND the backend SHALL validate the token via `djangorestframework-simplejwt`
- AND if the token is invalid or expired, the backend SHALL return `{"code": 401}`

#### Scenario: Current user info — [Status: Implemented]

- GIVEN a valid JWT access token
- WHEN `GET /api/auth/me/` is called
- THEN the backend SHALL return `{"code": 200, "data": {"id": <int>, "username": "<str>", "role": "<admin|operator>"}}`

#### Scenario: User logout — [Status: Implemented]

- GIVEN a valid JWT access token
- WHEN `POST /api/auth/logout/` is called
- THEN the backend SHALL return success (JWT is stateless; frontend discards the token)
- AND the frontend SHALL remove `factoryVisionToken` and `factoryVisionUser` from `localStorage`
- **Note:** On successful login, the frontend stores both `factoryVisionToken` (JWT string) and `factoryVisionUser` (JSON-serialized user object `{id, username, role}`) in `localStorage`

#### Scenario: Frontend auth guard — [Status: Implemented]

- GIVEN a user navigates to any route except `/login`
- WHEN the Vue Router `beforeEach` guard runs
- THEN if no `factoryVisionToken` exists in `localStorage`, the user SHALL be redirected to `/login?redirect=<original_path>`
- AND if a token exists and the user navigates to `/login`, they SHALL be redirected to `/dashboard`

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Authentication & Authorization in the Factory Vision system.


## User Model — [Status: Implemented]

The custom `User` model (table: `user`, extends Django `AbstractUser`) SHALL have:

| Field | Type | Description |
|-------|------|-------------|
| `username` | CharField | Inherited from AbstractUser |
| `password` | CharField | Inherited, hashed |
| `role` | CharField(32) | choices: `admin`(管理员) / `operator`(安保员), default=`operator` |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto_now |

**Settings:**
- `AUTH_USER_MODEL = "users.User"`
- `SIMPLE_JWT`: Access token lifetime = 24 hours, Refresh token = 7 days, Auth header type = Bearer
- `DEFAULT_AUTHENTICATION_CLASSES`: `JWTAuthentication`

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Authentication & Authorization in the Factory Vision system.


## Authorization — [Status: Partial]

- [ ] **Role-based access control:** The `role` field (admin/operator) is defined but not enforced by any permission class or middleware beyond `IsAuthenticated`. API endpoints use `@permission_classes([IsAuthenticated])` without role checks.
- [ ] **Employee creation endpoint:** `POST /api/employees/` has no `@permission_classes` decorator (public access). This is a known security risk — any unauthenticated caller can create employee records. The permission model (e.g., `IsAuthenticated` or admin-only) is pending team decision. This spec records the current state and does not prescribe the resolution.

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Authentication & Authorization in the Factory Vision system.


## ⚠️ Known Risks

| Risk | Detail | Status |
|------|--------|--------|
| `POST /api/employees/` 无鉴权 | 未登录用户即可创建员工记录（`employees/views.py:23` 无 `@permission_classes`）。权限收紧方案（`IsAuthenticated` 或 admin-only）待团队决策。 | Open |

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Authentication & Authorization in the Factory Vision system.


## Constraints

- JWT tokens are stateless — the backend does not maintain a token blacklist.
- Token refresh is configured (7-day refresh token) but the frontend currently only uses the access token.
- Passwords are stored using Django's default PBKDF2 hasher.
- The frontend stores the token in `localStorage` (key: `factoryVisionToken`). This is vulnerable to XSS; a future migration to httpOnly cookie should be evaluated as a security hardening measure.

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Authentication & Authorization in the Factory Vision system.


## 变更说明

| 说明 |
|------|
| 全新 spec，基于 `backend/apps/users/models.py`, `views.py`, `serializers.py`, `urls.py`, `tests.py` (5 tests) |
| 基于 `frontend/src/views/LoginView.vue`, `router/index.js`, `api/http.js`, `api/modules.js` |
| 基于 `backend/config/settings.py` 中 `SIMPLE_JWT` 和 `AUTH_USER_MODEL` 配置 |
