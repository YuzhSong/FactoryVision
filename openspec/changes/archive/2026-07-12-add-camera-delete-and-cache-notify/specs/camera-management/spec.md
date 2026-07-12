## ADDED Requirements

### Requirement: Delete camera

The system SHALL allow administrators to delete a camera, cascading to zones.

#### Scenario: Delete existing camera

- **GIVEN** camera id=1 exists with zones
- **WHEN** `DELETE /api/cameras/1/delete/` is called
- **THEN** camera and associated zones SHALL be deleted
- **AND** the backend SHALL notify AI Service via `POST /cache/cameras/reload`

## MODIFIED Requirements

### Requirement: Camera list and search

After creating, editing, toggling, or deleting a camera, the backend SHALL notify AI Service to reload its camera cache via `POST /cache/cameras/reload`.

#### Scenario: Mutations notify AI cache

- **GIVEN** the user modifies a camera (create/edit/toggle/delete)
- **WHEN** the operation succeeds
- **THEN** the backend SHALL call `POST /cache/cameras/reload` to refresh AI Service cache
