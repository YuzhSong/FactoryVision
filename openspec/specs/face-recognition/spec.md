# Face Recognition

## Purpose

Defines face enrollment, feature extraction, library synchronization, live matching, and cache invalidation.

## Requirements

### Requirement: Face feature extraction

AIService SHALL extract normalized face embeddings for qualified enrollment images.

#### Scenario: Extract enrolled face

- **GIVEN** Backend sends a valid face image to `POST /faces/extract`
- **WHEN** InsightFace detects a qualified face
- **THEN** AIService SHALL return one normalized 512-dimensional feature vector
- **AND** SHALL reject undecodable, face-free, or low-quality images with a clear error

### Requirement: Backend face enrollment

Backend SHALL persist one face record per employee angle and SHALL coordinate AIService refresh.

#### Scenario: Enroll one to three angles

- **GIVEN** an employee exists
- **WHEN** Frontend submits one to three front/left/right images through `POST /api/face/enroll/`
- **THEN** Backend SHALL extract and persist each feature and image
- **AND** a new image for the same angle SHALL replace the old record
- **AND** Backend SHALL notify AIService to refresh its library

#### Scenario: Query face slots

- **GIVEN** an employee has any subset of face angles
- **WHEN** `GET /api/employees/{id}/faces/` is called
- **THEN** the response SHALL contain front, left, and right slots with null for missing angles

### Requirement: Live face recognition

AIService SHALL compare detected faces against the loaded employee face library.

#### Scenario: Match a face

- **GIVEN** AIService has loaded the Backend face library
- **WHEN** a detected face is assigned to a person track
- **THEN** it SHALL compare normalized embeddings by cosine similarity
- **AND** SHALL return employee identity only when the configured threshold is met
- **AND** otherwise SHALL return an unknown result

### Requirement: Face library cache shall reflect mutations

AIService SHALL invalidate face-library and track-identity caches after relevant mutations.

#### Scenario: Employee or face deletion

- **GIVEN** an employee or face record is removed
- **WHEN** AIService reloads the library
- **THEN** removed records SHALL disappear from matching data
- **AND** short-lived track identity caches SHALL be invalidated so stale labels are not reused
