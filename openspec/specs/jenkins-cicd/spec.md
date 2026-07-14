# Jenkins CI/CD

## Purpose

Defines validation, image build, cloud deployment, migration, health check, and cleanup for the production Frontend and Backend stack.

## Requirements

### Requirement: Validate cloud-side code

Jenkins SHALL validate production configuration and buildability before deployment.

#### Scenario: Validate repository

- **GIVEN** Jenkins checked out a commit
- **WHEN** validation runs
- **THEN** production Compose configuration SHALL be valid
- **AND** Frontend SHALL complete a production build
- **AND** Backend SHALL pass `manage.py check`

### Requirement: Build production images

Jenkins SHALL build the production Backend and Frontend images.

#### Scenario: Build application images

- **GIVEN** validation passed
- **WHEN** the build stage runs
- **THEN** Jenkins SHALL build Backend and Frontend images from their Dockerfiles

### Requirement: Deploy cloud stack

Jenkins SHALL deploy the PostgreSQL, Backend, and Frontend cloud stack and run required migrations.

#### Scenario: Update services

- **GIVEN** `deploy/.env.prod` is present
- **WHEN** deployment runs
- **THEN** Compose SHALL update PostgreSQL, Backend, and Frontend
- **AND** Backend migrations and collectstatic SHALL run non-interactively
- **AND** service and HTTP health checks SHALL complete

### Requirement: Keep AIService outside cloud deployment

The cloud pipeline SHALL leave the independently managed AIService untouched.

#### Scenario: Deploy web stack

- **GIVEN** AIService depends on local GPU, models, and stream access
- **WHEN** Jenkins deploys the cloud stack
- **THEN** it SHALL NOT build or restart AIService

### Requirement: Clean dangling images

Jenkins SHALL remove dangling images after deployment without deleting active data.

#### Scenario: Deployment completes

- **WHEN** the cleanup stage runs
- **THEN** dangling Docker images SHALL be pruned without removing active service images or persistent volumes
