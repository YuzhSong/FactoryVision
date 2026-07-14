# Authentication and Authorization

## Purpose

Defines JWT authentication, protected application routes, and authenticated business APIs.

## Requirements

### Requirement: JWT login

Backend SHALL authenticate active users and issue JWT credentials for valid logins.

#### Scenario: Valid credentials

- **GIVEN** an active user supplies valid credentials
- **WHEN** `POST /api/auth/login/` is called
- **THEN** Backend SHALL return access/refresh credentials and user information

#### Scenario: Invalid credentials

- **GIVEN** credentials are invalid
- **WHEN** login is attempted
- **THEN** Backend SHALL return an authentication error without revealing sensitive account details

### Requirement: Current user and logout

The system SHALL expose the current authenticated identity and SHALL support ending the frontend session.

#### Scenario: Query current session

- **GIVEN** a valid Bearer token
- **WHEN** `GET /api/auth/me/` is called
- **THEN** Backend SHALL return the authenticated user

#### Scenario: Logout

- **GIVEN** the user is logged in
- **WHEN** logout completes
- **THEN** Frontend SHALL clear locally stored credentials and protected routes SHALL no longer be accessible

### Requirement: Protected business operations

Backend SHALL require authentication for business data mutations and protected queries.

#### Scenario: Unauthenticated request

- **GIVEN** no valid JWT is supplied
- **WHEN** a protected employee, camera, zone, alert, dashboard, face, event, or report operation is called
- **THEN** Backend SHALL reject the request

### Requirement: Frontend route guard

Frontend SHALL prevent unauthenticated navigation to protected application routes.

#### Scenario: Open protected page

- **GIVEN** no token is stored
- **WHEN** a user navigates to an application route
- **THEN** Frontend SHALL redirect to `/login` and preserve the intended redirect target

Role values `admin` and `operator` are stored for display and future policy refinement; the current version primarily enforces authenticated access rather than per-role permissions.
