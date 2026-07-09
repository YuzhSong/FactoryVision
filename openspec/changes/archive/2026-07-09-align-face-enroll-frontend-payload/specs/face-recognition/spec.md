## ADDED Requirements

### Requirement: Backend face enrollment API

The system SHALL accept employee face enrollment through a backend API that receives exactly three face images for one employee.

#### Scenario: Enroll three face images

- **GIVEN** a valid JWT access token and an existing employee
- **WHEN** `POST /api/face/enroll/` is called with `employeeId` and `faces`
- **THEN** `faces` SHALL contain exactly three items
- **AND** each item SHALL contain `imageBase64` and `faceType`
- **AND** the allowed `faceType` values SHALL be `front`, `left`, and `right`
- **AND** the response SHALL return `results` with `faceType` and `faceFeatureId` for each saved face feature

#### Scenario: Reject incomplete face enrollment

- **GIVEN** the request body contains fewer or more than three face images
- **WHEN** `POST /api/face/enroll/` is called
- **THEN** the backend SHALL reject the request with a validation error
