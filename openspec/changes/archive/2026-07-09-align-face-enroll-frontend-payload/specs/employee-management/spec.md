## ADDED Requirements

### Requirement: Frontend face enrollment payload

The employee management frontend SHALL submit face enrollment data using the backend face enrollment API contract.

#### Scenario: Submit captured front, left, and right face photos

- **GIVEN** an employee has selected or captured front, left, and right face photos
- **WHEN** the user submits face enrollment
- **THEN** the frontend SHALL call `POST /api/face/enroll/`
- **AND** the request body SHALL include `employeeId`
- **AND** the request body SHALL include `faces` with one `front`, one `left`, and one `right` item
- **AND** each item SHALL include the corresponding `imageBase64`
