# Employee Management

> **Status:** ⚠️ 已更新 —— 后端 CRUD 已完成，前端仍为占位

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Employee Management in the Factory Vision system.
## Requirements
### Requirement: Employee CRUD Operations

The system SHALL provide employee creation and list querying through the backend API. The employee management frontend SHALL use the backend employee APIs instead of hardcoded placeholder data.

#### Scenario: Create a new employee

- **GIVEN** a valid request body with `employeeNo`, `name`, and optional `department`, `position`, `phone`
- **WHEN** `POST /api/employees/` is called
- **THEN** a new `Employee` record SHALL be created with status defaulting to `"active"`
- **AND** the response SHALL return `{"code": 200, "data": {"id": <new_id>}}`
- **AND** if `employeeNo` already exists, the response SHALL return `{"code": 409, "message": "工号 {id} 已存在"}`

#### Scenario: List employees with pagination and filtering

- **GIVEN** a valid JWT access token in the `Authorization: Bearer <token>` header
- **WHEN** `GET /api/employees/list/?page=1&pageSize=20&keyword=张&department=生产部&status=active` is called
- **THEN** the response SHALL return `{"code": 200, "data": {"total": <int>, "items": [...]}}`
- **AND** each item SHALL contain fields: `id`, `employeeNo`, `name`, `department`, `position`, `phone`, `status`

#### Scenario: Frontend displays backend employee data

- **GIVEN** the user is authenticated and navigates to `/employees`
- **WHEN** the EmployeesView page renders
- **THEN** the frontend SHALL call `employeesApi.list()`
- **AND** the table SHALL render backend `items`
- **AND** keyword, department, and status filters SHALL be sent as query params
- **AND** after successful employee creation the table SHALL refresh

### Requirement: Frontend face enrollment payload

The employee management frontend SHALL submit face enrollment data using the backend face enrollment API contract.

#### Scenario: Submit captured front, left, and right face photos

- **GIVEN** an employee has selected or captured front, left, and right face photos
- **WHEN** the user submits face enrollment
- **THEN** the frontend SHALL call `POST /api/face/enroll/`
- **AND** the request body SHALL include `employeeId`
- **AND** the request body SHALL include `faces` with one `front`, one `left`, and one `right` item
- **AND** each item SHALL include the corresponding `imageBase64`

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Employee Management in the Factory Vision system.

## Employee Model — [Status: Implemented]

The `Employee` model (table: `employee`) SHALL have the following fields:

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | BigAutoField | PK, auto | Primary key |
| `employee_no` | CharField(64) | unique, required | 工号 |
| `name` | CharField(64) | required | 姓名 |
| `department` | CharField(128) | optional, default="" | 部门 |
| `position` | CharField(128) | optional, default="" | 岗位 |
| `phone` | CharField(32) | optional, default="" | 手机号 |
| `status` | CharField(32) | choices: `active`(在职) / `inactive`(停用), default=`active` | 状态 |
| `created_at` | DateTimeField | auto_now_add | 创建时间 |
| `updated_at` | DateTimeField | auto_now | 更新时间 |

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Employee Management in the Factory Vision system.

## Planned Features (Not Yet Implemented)

- [ ] **Employee Update (PUT/PATCH):** No update endpoint exists
- [ ] **Employee Delete:** No delete endpoint exists
- [ ] **Frontend API Integration:** `EmployeesView.vue` SHALL call `employeesApi.list()` / `employeesApi.create()` instead of using `data/placeholders.js`
- [ ] **POST /api/employees/ authentication:** Currently has no `@permission_classes` decorator — any caller (including unauthenticated) can create employees. Permission model pending team decision.
- [ ] **Face enrollment workflow:** UI shows "录入占位" button; backend has no face enrollment API

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Employee Management in the Factory Vision system.

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Employee Management in the Factory Vision system.

## ⚠️ Known Risks

| Risk | Detail | Status |
|------|--------|--------|
| `POST /api/employees/` 无鉴权 | 未登录用户即可创建员工记录（`employees/views.py:23` 无 `@permission_classes`）。权限收紧方案（`IsAuthenticated` 或 admin-only）待团队决策。 | Open |

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Employee Management in the Factory Vision system.

## Constraints

- Employee `status` field is not exposed in the create serializer — new employees always default to `"active"`. Changing status requires direct DB access or a future update endpoint.
- The `employee_root_view` handles both GET (placeholder) and POST (create) on the same URL path — this is a compact design that may be split in the future.

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Employee Management in the Factory Vision system.

## 变更说明

| 变更 | 原 spec | 新草稿 | 依据 |
|------|---------|--------|------|
| 新增 Employee Model 定义 | 无 | 完整字段表 | `backend/apps/employees/models.py` |
| 新增 POST /api/employees/ 场景 | 无（仅说 placeholder） | 创建员工 + 重复检测 | `backend/apps/employees/views.py` L27-55 |
| 新增 GET /api/employees/list/ 场景 | 无 | 分页 + 过滤 + 认证 | `backend/apps/employees/views.py` L58-89 |
| 保留占位页面场景 | "placeholder page" | 更新为描述实际 UI 状态 | `frontend/src/views/EmployeesView.vue` |
| 新增 Planned Features 节 | 无 | 列出 Update/Delete/前端对接等 | 代码分析 |
| 保留 Constraints | 无 | 新增 status 不可创建、POST 无认证 | 代码分析 |
