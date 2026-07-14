# Attendance

## Purpose

Records the explicitly deferred attendance boundary for future first-seen, leave, return, and duration statistics.

## Requirements

### Requirement: Keep attendance outside the current delivery scope

The current release SHALL treat attendance as a deferred extension boundary.

#### Scenario: Inspect current version

- **GIVEN** the final project version is deployed
- **WHEN** attendance capability is reviewed
- **THEN** Backend MAY retain a placeholder module boundary
- **AND** Frontend SHALL NOT advertise an unfinished attendance page in primary navigation
- **AND** future attendance work SHALL require a new OpenSpec change
