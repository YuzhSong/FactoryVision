## MODIFIED Requirements

### Requirement: Zone list with Swagger documentation

The zone list endpoint SHALL display Chinese Swagger annotations and response examples.

#### Scenario: List zones by camera

- **GIVEN** the user selects a camera in `/zones`
- **WHEN** `GET /api/zones/list/?cameraId=1` is called
- **THEN** the response SHALL include fields: `id`, `name`, `cameraId`, `type`, `points`, `enabled`, `description`

## ADDED Requirements

### Requirement: Zone creation API

The backend SHALL provide a zone creation endpoint for configuring detection zones.

#### Scenario: Create a danger zone for a camera

- **GIVEN** the user is authenticated and camera id=1 exists
- **WHEN** `POST /api/zones/` is called with `{cameraId, name, type, points, enabled, description}`
- **THEN** the backend SHALL create a new zone record
- **AND** return `{id}` with HTTP 200

#### Scenario: Points validation

- **GIVEN** the user submits a zone with fewer than 3 points
- **WHEN** `POST /api/zones/` is called
- **THEN** the backend SHALL return HTTP 422 with message "多边形至少需要 3 个顶点"

#### Scenario: Camera not found

- **GIVEN** the cameraId does not exist
- **WHEN** `POST /api/zones/` is called
- **THEN** the backend SHALL return HTTP 404
