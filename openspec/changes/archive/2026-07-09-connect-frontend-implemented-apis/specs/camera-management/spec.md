## ADDED Requirements

### Requirement: Frontend camera list integration

The camera management frontend SHALL display camera data from the implemented backend camera list API.

#### Scenario: Load camera list

- **GIVEN** the user opens `/cameras`
- **WHEN** `GET /api/cameras/list/` succeeds
- **THEN** the camera table SHALL render backend `items`
- **AND** status filter SHALL be passed as a query param when selected
- **AND** unsupported create/edit actions SHALL remain marked as planned
