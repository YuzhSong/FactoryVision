## ADDED Requirements

### Requirement: Frontend warning zone list integration

The warning zone frontend SHALL display detection zones from the implemented backend zone list API.

#### Scenario: Load zones by selected camera

- **GIVEN** cameras are loaded from the backend
- **WHEN** the user selects a camera in `/zones`
- **THEN** the frontend SHALL call `GET /api/zones/list/?cameraId=<id>`
- **AND** the zone table SHALL render backend `items`
- **AND** unsupported polygon editing and saving actions SHALL remain marked as planned
