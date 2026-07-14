## MODIFIED Requirements

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
