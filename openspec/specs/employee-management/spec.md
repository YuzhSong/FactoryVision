# Employee Management

## Purpose

Defines employee CRUD and its integration with face enrollment and AIService cache refresh.

## Requirements

### Requirement: Employee CRUD

Backend SHALL provide authenticated create, list, update, and delete operations for employees.

#### Scenario: Create employee

- **GIVEN** the user submits a unique employee number and required name
- **WHEN** `POST /api/employees/` is called
- **THEN** Backend SHALL create and return the employee
- **AND** duplicate employee numbers SHALL be rejected

#### Scenario: List employees

- **GIVEN** employee records exist
- **WHEN** `GET /api/employees/list/` is called
- **THEN** Backend SHALL support pagination, keyword, department, and status filters

#### Scenario: Update employee

- **GIVEN** an employee exists
- **WHEN** `PUT /api/employees/{id}/` receives valid partial fields
- **THEN** Backend SHALL update the record and notify AIService to refresh relevant cached data

#### Scenario: Delete employee

- **GIVEN** an employee exists
- **WHEN** `DELETE /api/employees/{id}/delete/` is called
- **THEN** Backend SHALL remove employee-owned face records and images
- **AND** SHALL notify AIService so stale identity labels are invalidated

### Requirement: Frontend employee workflow

Frontend SHALL provide an API-backed employee and face-management workflow.

#### Scenario: Manage employee and faces

- **GIVEN** an authenticated user opens `/employees`
- **WHEN** records are created, edited, deleted, or selected for face enrollment
- **THEN** Frontend SHALL use Backend APIs and update the visible list
- **AND** SHALL expose front/left/right face slots and clear error messages
