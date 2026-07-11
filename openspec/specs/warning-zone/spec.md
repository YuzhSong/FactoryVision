# Warning Zone

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Warning Zone in the Factory Vision system.
## Requirements
### Requirement: Reserve Warning Zone Management

The system SHALL provide frontend and backend module boundaries for future warning zone configuration.

#### Scenario: Access zone configuration placeholder

- GIVEN the project skeleton is running
- WHEN a user opens the zone configuration page
- THEN the frontend SHALL display a placeholder page for future polygon editing

### Requirement: Frontend warning zone list integration

The warning zone frontend SHALL display detection zones from the implemented backend zone list API.

#### Scenario: Load zones by selected camera

- **GIVEN** cameras are loaded from the backend
- **WHEN** the user selects a camera in `/zones`
- **THEN** the frontend SHALL call `GET /api/zones/list/?cameraId=<id>`
- **AND** the zone table SHALL render backend `items`
### Requirement: Zone creation API

The backend SHALL provide a zone creation endpoint for administrators to configure detection zones.

#### Scenario: Create a danger zone for a camera

- **GIVEN** the user is authenticated
- **WHEN** the frontend sends `POST /api/zones/` with `{cameraId, name, type, points, enabled, description}`
- **THEN** the backend SHALL create a new zone record linked to the specified camera
- **AND** SHALL return `{id}` with HTTP 200
- **AND** points with fewer than 3 entries SHALL return HTTP 422

#### Scenario: Zone list with Swagger documentation

- **GIVEN** the backend is running
- **WHEN** the developer opens `/api/docs/`
- **THEN** all zone endpoints SHALL display Chinese descriptions and response examples

