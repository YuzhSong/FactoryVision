## MODIFIED Requirements

### Requirement: Backend face enrollment API

The face list endpoint SHALL return a three-slot object (front/left/right) with null for missing faces.

#### Scenario: Query faces with all three slots

- **GIVEN** employee has only front and left faces
- **WHEN** `GET /api/employees/{id}/faces/` is called
- **THEN** front and left slots SHALL contain face data
- **AND** right slot SHALL be null
