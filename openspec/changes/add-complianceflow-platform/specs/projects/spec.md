# Project Management

## ADDED Requirements

### Requirement: Project CRUD Operations

The system SHALL provide endpoints to create, read, update, and delete projects.

#### Scenario: Create project

- **WHEN** an Author calls `POST /api/v1/projects` with name, local_path, compliance_standard
- **THEN** the system creates project record
- **AND** validates the local_path exists and is accessible
- **AND** runs `openspec init --standard {standard}` in the directory
- **AND** returns the created project with id

#### Scenario: Create project invalid path

- **WHEN** an Author provides a non-existent or inaccessible path
- **THEN** the system returns 400 Bad Request
- **AND** includes error describing the path issue

#### Scenario: List projects

- **WHEN** a user calls `GET /api/v1/projects`
- **THEN** the system returns paginated list of projects the user has access to

#### Scenario: Get project details

- **WHEN** a user calls `GET /api/v1/projects/{id}`
- **THEN** the system returns project details including compliance standard and lock status

#### Scenario: Update project

- **WHEN** an Admin or project owner calls `PUT /api/v1/projects/{id}`
- **THEN** the system updates allowed fields (name)
- **AND** validates changes
- **AND** logs update to audit trail

#### Scenario: Delete project

- **WHEN** an Admin calls `DELETE /api/v1/projects/{id}`
- **THEN** the system soft-deletes the project record
- **AND** does not delete files from filesystem
- **AND** logs deletion to audit trail

### Requirement: Project Locking

The system SHALL support advisory locks to prevent concurrent CLI operations.

#### Scenario: Acquire project lock

- **WHEN** a user calls `POST /api/v1/projects/{id}/lock`
- **AND** the project is not currently locked
- **THEN** the system sets locked_by to current user
- **AND** sets locked_at to current timestamp
- **AND** returns lock confirmation

#### Scenario: Lock already held

- **WHEN** a user attempts to lock an already-locked project
- **THEN** the system returns 409 Conflict
- **AND** includes lock holder information and lock time

#### Scenario: Release project lock

- **WHEN** the lock holder calls `DELETE /api/v1/projects/{id}/lock`
- **THEN** the system clears locked_by and locked_at
- **AND** allows other users to acquire lock

#### Scenario: Admin force unlock

- **WHEN** an Admin calls `DELETE /api/v1/projects/{id}/lock?force=true`
- **THEN** the system releases the lock regardless of holder
- **AND** logs the force unlock to audit trail

#### Scenario: Lock expiry

- **WHEN** a lock has been held for more than 30 minutes
- **THEN** the system automatically releases the lock
- **AND** logs the expiry to audit trail

### Requirement: Compliance Standard Configuration

The system SHALL enforce a single compliance standard per project.

#### Scenario: Standard set on creation

- **WHEN** a project is created
- **THEN** the compliance_standard field is required
- **AND** must be one of: IEC_62304, ISO_26262, DO_178C, CUSTOM

#### Scenario: Standard immutable after creation

- **WHEN** a user attempts to change project compliance_standard
- **THEN** the system returns 400 Bad Request
- **AND** indicates standard cannot be changed after creation

### Requirement: OpenSpec JSON Validation

The system SHALL validate `openspec.json` exists and conforms to schema.

#### Scenario: Valid openspec.json

- **WHEN** loading a project
- **THEN** the system reads and validates `openspec.json`
- **AND** stores parsed configuration

#### Scenario: Missing openspec.json

- **WHEN** `openspec.json` is missing from project path
- **THEN** the system returns error indicating initialization required

#### Scenario: Invalid openspec.json schema

- **WHEN** `openspec.json` fails schema validation
- **THEN** the system returns 400 Bad Request
- **AND** includes specific validation errors

### Requirement: Optimistic Locking

The system SHALL use optimistic locking to prevent lost updates.

#### Scenario: Update with correct version

- **WHEN** a user updates a project with matching version number
- **THEN** the system applies the update
- **AND** increments the version number

#### Scenario: Update with stale version

- **WHEN** a user updates a project with outdated version number
- **THEN** the system returns 409 Conflict
- **AND** includes current version for client retry
