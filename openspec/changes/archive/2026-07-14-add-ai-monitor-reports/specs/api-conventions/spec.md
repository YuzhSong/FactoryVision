## ADDED Requirements

### Requirement: Report API conventions

Report JSON APIs SHALL follow the project API response envelope and authentication conventions.

#### Scenario: Authenticated report JSON response

- WHEN an authenticated user calls a report JSON endpoint
- THEN the response SHALL use `code`, `message`, `data`, and `requestId`
- AND list endpoints SHALL accept `page` and `pageSize`

#### Scenario: Unauthenticated report request

- WHEN a user without a valid Bearer token calls a report endpoint
- THEN protected endpoints SHALL reject the request with an authentication error
