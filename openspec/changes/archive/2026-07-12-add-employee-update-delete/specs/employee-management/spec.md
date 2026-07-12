## ADDED Requirements

### Requirement: Update employee

The system SHALL allow administrators to update employee information and notify AI Service.

#### Scenario: Partial update

- **GIVEN** the user is authenticated and employee id=1 exists
- **WHEN** `PUT /api/employees/1/` is called with `{name:"张三", department:"质检部"}`
- **THEN** only those fields SHALL be updated, others unchanged
- **AND** the backend SHALL notify AI Service via `POST /cache/employees/upsert`

#### Scenario: Employee not found

- **GIVEN** employee id=999 does not exist
- **WHEN** `PUT /api/employees/999/` is called
- **THEN** the backend SHALL return HTTP 404

### Requirement: Delete employee

The system SHALL allow administrators to delete an employee, cascading to face_feature and local images.

#### Scenario: Delete with faces

- **GIVEN** employee id=1 exists with 3 face_features
- **WHEN** `DELETE /api/employees/1/` is called
- **THEN** employee + all face_features SHALL be deleted
- **AND** local images under `media/faces/1/` SHALL be removed
- **AND** the backend SHALL notify AI Service via `POST /cache/employees/delete`

#### Scenario: Employee not found when deleting

- **GIVEN** employee id=999 does not exist
- **WHEN** `DELETE /api/employees/999/` is called
- **THEN** the backend SHALL return HTTP 404
