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
- **AND** unsupported polygon editing and saving actions SHALL remain marked as planned

