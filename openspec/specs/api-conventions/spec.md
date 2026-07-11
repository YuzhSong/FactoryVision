# API Conventions

> **Status:** 新建 —— 统一响应格式是全项目的基础契约

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for API Conventions in the Factory Vision system.


## Requirements

### Requirement: Unified API Response Format

The system SHALL use a consistent JSON response envelope for all API endpoints. Every response SHALL include a status code, human-readable message, payload data, and a unique request identifier for tracing.

#### Scenario: Successful response — [Status: Implemented]

- GIVEN any API endpoint processes a valid request successfully
- WHEN the response is generated via `api_response()`
- THEN the response body SHALL follow this structure:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": <any valid JSON>,
    "requestId": "<UUID v4>"
  }
  ```
- AND the HTTP status code SHALL match the `code` field when it represents an HTTP-level status

#### Scenario: Error response (handled by application) — [Status: Implemented]

- GIVEN an API endpoint encounters a handled error (validation failure, conflict, not found, etc.)
- WHEN the response is generated via `api_response(code=<n>, message="<detail>", data=...)`
- THEN the response body SHALL use the same envelope with a non-200 `code`:
  ```json
  {
    "code": 400,
    "message": "请求参数错误",
    "data": <validation errors or null>,
    "requestId": "<UUID v4>"
  }
  ```

#### Scenario: Error response (unhandled DRF exception) — [Status: Implemented]

- GIVEN an unhandled exception occurs (permission denied, not found, method not allowed, etc.)
- WHEN the `custom_exception_handler` processes the exception
- THEN the response body SHALL be normalized into the same envelope format:
  ```json
  {
    "code": <HTTP status code>,
    "message": "<exception detail string>",
    "data": null,
    "requestId": "<UUID v4>"
  }
  ```
- AND the original DRF error structure SHALL be flattened into a single `message` string

#### Scenario: Paginated list response — [Status: Implemented]

- GIVEN an API endpoint returns a paginated list
- WHEN the response is generated
- THEN the `data` field SHALL contain:
  ```json
  {
    "total": <int>,
    "items": [<array of serialized objects>]
  }
  ```
- AND pagination parameters SHALL be passed as query params: `page` (default 1), `pageSize` (default 20)

#### Scenario: Request tracing — [Status: Implemented]

- GIVEN any API request is processed
- WHEN the response is generated
- THEN a unique `requestId` (UUID v4) SHALL be included
- AND if the caller provides a `requestId` parameter, it SHALL be preserved in the response

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for API Conventions in the Factory Vision system.


## Response Code Conventions

| Code | Meaning | Example Usage |
|------|---------|--------------|
| 200 | Success | Standard successful response |
| 400 | Bad Request | Validation errors, invalid pagination |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | Account disabled (`"账号已被禁用"`) |
| 409 | Conflict | Duplicate `employeeNo` |

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for API Conventions in the Factory Vision system.


## Constraints

- All backend apps SHALL use `api_response()` from `common.response` instead of raw DRF `Response`.
- The frontend Axios response interceptor (`http.js:17`) unwraps `response.data`, so frontend code receives the envelope `{code, message, data, requestId}` directly without an extra `.data` layer.
- `custom_exception_handler` is registered in `REST_FRAMEWORK["EXCEPTION_HANDLER"]` in `settings.py` and applies globally to all DRF views.

---


## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for API Conventions in the Factory Vision system.


## 变更说明

| 说明 |
|------|
| 全新 spec，基于 `backend/common/response.py` 中的 `api_response()` 和 `custom_exception_handler()` |
| 基于全部 7 个 backend app 的统一使用模式 |
| 基于 `frontend/src/views/LoginView.vue` 中的 `response.code !== 200` 检查逻辑 |
| pagination 格式基于 `backend/apps/employees/views.py` 的实现 |
