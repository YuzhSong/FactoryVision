## MODIFIED Requirements

### Requirement: Backend face enrollment API

The face enrollment endpoint SHALL accept 1-3 faces and auto-replace existing same-faceType records per employee.

#### Scenario: Replace existing same faceType

- **GIVEN** employee id=3 has a front face record
- **WHEN** `POST /api/face/enroll/` with `{employeeId:3, faces:[{faceType:"front",...}]}`
- **THEN** the old front record and its image SHALL be deleted
- **AND** a new front record SHALL be created

#### Scenario: Partial enrollment with 1 face

- **GIVEN** employee id=3 has no face records
- **WHEN** `POST /api/face/enroll/` with only one face
- **THEN** the backend SHALL accept and create only that record
