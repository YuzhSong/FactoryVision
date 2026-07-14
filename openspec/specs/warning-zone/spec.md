# Warning Zone

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Warning Zone in the Factory Vision system.
## Requirements
### Requirement: Reserve Warning Zone Management

The system SHALL provide a frontend polygon editor for warning zone configuration and submit valid drafts to the implemented backend creation API.

#### Scenario: Draft a warning zone polygon on the frontend

- GIVEN a user opens the zone configuration page and selects a camera
- WHEN the user clicks inside the monitor area
- THEN the frontend SHALL add a polygon point at the clicked location
- AND the point SHALL be stored as normalized coordinates between 0 and 1
- AND the frontend SHALL render the polygon preview over the monitor area
- AND the user SHALL be able to drag existing points to adjust the polygon
- AND the user SHALL be able to undo the last point or clear the draft
- AND the frontend SHALL require a zone name before saving
- AND the frontend SHALL call `POST /api/zones/` with `{cameraId, name, type, points, enabled, description}` when saving a valid polygon
- AND the frontend SHALL refresh `GET /api/zones/list/?cameraId=<id>` after successful creation

### Requirement: Frontend warning zone list integration

The warning zone frontend SHALL display detection zones from the implemented backend zone list API and SHALL allow users to preview a saved zone polygon from the zone list.

#### Scenario: Load zones by selected camera

- **GIVEN** cameras are loaded from the backend
- **WHEN** the user selects a camera in `/zones`
- **THEN** the frontend SHALL call `GET /api/zones/list/?cameraId=<id>`
- **AND** the zone table SHALL render backend `items`

#### Scenario: Preview selected saved zone on editor

- **GIVEN** zones are loaded for the selected camera
- **WHEN** the user clicks a zone row in the zone list
- **THEN** the frontend SHALL highlight the selected row
- **AND** the frontend SHALL render that zone's saved polygon points over the editor area
- **AND** the preview SHALL use the same normalized coordinates stored in `points`

#### Scenario: Clear saved-zone preview when drafting

- **GIVEN** a saved zone polygon is being previewed
- **WHEN** the user clicks the editor area to add a new draft point
- **THEN** the frontend SHALL clear the selected saved-zone preview
- **AND** the new draft polygon SHALL be shown independently from the saved-zone preview

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

