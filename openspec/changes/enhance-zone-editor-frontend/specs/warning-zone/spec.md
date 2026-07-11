## MODIFIED Requirements

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

The warning zone frontend SHALL display detection zones from the implemented backend zone list API.

#### Scenario: Load zones by selected camera

- **GIVEN** cameras are loaded from the backend
- **WHEN** the user selects a camera in `/zones`
- **THEN** the frontend SHALL call `GET /api/zones/list/?cameraId=<id>`
- **AND** the zone table SHALL render backend `items`
