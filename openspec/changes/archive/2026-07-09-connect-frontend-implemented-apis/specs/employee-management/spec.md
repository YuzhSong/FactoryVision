## MODIFIED Requirements

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
