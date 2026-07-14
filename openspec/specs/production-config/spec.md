# Production Configuration and Security

## Purpose

Defines environment-driven production configuration for the deployed web stack.

## Requirements

### Requirement: Production secrets and hosts

Production Backend SHALL receive secrets and allowed origins from environment configuration.

#### Scenario: Start Backend in production

- **GIVEN** the production Compose starts Backend
- **WHEN** environment variables are loaded
- **THEN** a non-development Django secret key, allowed hosts, CSRF origins, CORS origins, Backend API token, and database credentials SHALL be provided
- **AND** debug mode SHALL be disabled
- **AND** secrets SHALL NOT be committed

### Requirement: PostgreSQL production database

Production Backend SHALL use PostgreSQL while local development MAY use SQLite.

#### Scenario: Connect database

- **GIVEN** the production stack is started
- **WHEN** Backend initializes
- **THEN** it SHALL connect to the PostgreSQL service using environment-provided credentials
- **AND** local SQLite SHALL remain the development default only

### Requirement: Containerized web deployment

The production web stack SHALL run Backend and Frontend from container images.

#### Scenario: Serve application

- **GIVEN** production images were built
- **WHEN** Compose starts the stack
- **THEN** Frontend SHALL be served by Nginx
- **AND** Backend SHALL be served by Daphne/ASGI
- **AND** static and media volumes SHALL be mounted read-only into the Frontend container where appropriate

### Requirement: HTTPS termination

Production public traffic SHALL use origins and proxy settings consistent with HTTPS termination.

#### Scenario: Access production site

- **GIVEN** an external reverse proxy or Nginx terminates TLS
- **WHEN** Browser accesses Frontend, REST, WebSocket, or media URLs
- **THEN** public origins and proxy headers SHALL match the deployed HTTPS domain
