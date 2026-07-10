## MODIFIED Requirements

### Requirement: Camera list and search

The backend SHALL provide a camera list endpoint with keyword search, status filtering, and pagination. AI Service SHALL receive full results when omitting pagination parameters.

#### Scenario: List all cameras

- **GIVEN** camera records exist in the database
- **WHEN** `GET /api/cameras/list/` is called without pagination parameters
- **THEN** the backend SHALL return all cameras with fields: `id`, `name`, `code`, `streamUrl`, `processedStreamUrl`, `location`, `status`, `enabled`
- **AND** AI Service SHALL use this endpoint to discover camera stream URLs

#### Scenario: Search and filter cameras

- **GIVEN** the user is on the camera management page
- **WHEN** `GET /api/cameras/list/?keyword=车间&status=online&page=1&pageSize=20` is called
- **THEN** the backend SHALL return paginated results filtered by keyword (matches name, code, or location) and status

## ADDED Requirements

### Requirement: Camera creation

The backend SHALL provide a camera creation endpoint with auto-generated code.

#### Scenario: Create camera with auto-generated code

- **GIVEN** the user is authenticated
- **WHEN** `POST /api/cameras/` is called without a `code` field
- **THEN** the backend SHALL auto-generate a code in `CAM00N` format
- **AND** return `{id, code}` with HTTP 200

#### Scenario: Duplicate code rejected

- **GIVEN** a camera with code "CAM001" already exists
- **WHEN** `POST /api/cameras/` is called with `code:"CAM001"`
- **THEN** the backend SHALL return HTTP 409

### Requirement: Camera editing

The backend SHALL provide a camera update endpoint where all fields are optional.

#### Scenario: Partial update

- **GIVEN** camera id=1 exists
- **WHEN** `PUT /api/cameras/{id}/` is called with `{name:"新名称"}`
- **THEN** the backend SHALL update only that field, leaving others unchanged

### Requirement: Camera status toggle

The backend SHALL provide a status toggle endpoint.

#### Scenario: Toggle camera status

- **GIVEN** a camera with status "offline"
- **WHEN** `POST /api/cameras/{id}/toggle/` is called with `{status:"online"}`
- **THEN** the backend SHALL update status and return `{id, status}`
