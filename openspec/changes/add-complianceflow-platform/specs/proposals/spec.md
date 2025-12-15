# Proposal Lifecycle

## ADDED Requirements

### Requirement: Proposal CRUD Operations

The system SHALL provide endpoints to create, read, update, and delete change proposals.

#### Scenario: Create proposal

- **WHEN** an Author calls `POST /api/v1/projects/{project_id}/proposals` with name
- **THEN** the system creates proposal record with status DRAFT
- **AND** runs `openspec scaffold {name}` in project directory
- **AND** sets draft_path to the created directory
- **AND** logs creation to audit trail

#### Scenario: Create proposal duplicate name

- **WHEN** an Author creates a proposal with name that already exists in project
- **THEN** the system returns 409 Conflict

#### Scenario: List proposals

- **WHEN** a user calls `GET /api/v1/projects/{project_id}/proposals`
- **THEN** the system returns paginated list of proposals
- **AND** supports filtering by status
- **AND** supports search by name

#### Scenario: Get proposal details

- **WHEN** a user calls `GET /api/v1/proposals/{id}`
- **THEN** the system returns proposal details including status, created_by, approved_by

#### Scenario: Delete proposal

- **WHEN** an Author or Admin calls `DELETE /api/v1/proposals/{id}`
- **AND** proposal status is DRAFT
- **THEN** the system deletes proposal record
- **AND** optionally deletes draft files (based on query param)
- **AND** logs deletion to audit trail

#### Scenario: Delete non-draft proposal

- **WHEN** a user attempts to delete proposal not in DRAFT status
- **THEN** the system returns 400 Bad Request

### Requirement: Proposal Status Workflow

The system SHALL enforce status transitions: DRAFT → REVIEW → READY → MERGED.

#### Scenario: Submit for review

- **WHEN** an Author calls `POST /api/v1/proposals/{id}/submit`
- **AND** proposal is in DRAFT status
- **AND** validation passes
- **THEN** the system transitions status to REVIEW
- **AND** logs transition to audit trail

#### Scenario: Submit without validation

- **WHEN** an Author submits proposal that fails validation
- **THEN** the system returns 400 Bad Request
- **AND** includes validation errors

#### Scenario: Approve proposal

- **WHEN** a Reviewer calls `POST /api/v1/proposals/{id}/approve`
- **AND** proposal is in REVIEW status
- **THEN** the system transitions status to READY
- **AND** sets approved_by to current user
- **AND** logs approval to audit trail

#### Scenario: Request changes

- **WHEN** a Reviewer calls `POST /api/v1/proposals/{id}/request-changes`
- **AND** proposal is in REVIEW status
- **THEN** the system transitions status back to DRAFT
- **AND** logs the request to audit trail

#### Scenario: Merge proposal

- **WHEN** an Admin calls `POST /api/v1/proposals/{id}/merge`
- **AND** proposal is in READY status
- **THEN** the system runs OpenSpec merge/implement command
- **AND** transitions status to MERGED
- **AND** logs merge to audit trail

#### Scenario: Invalid status transition

- **WHEN** a user attempts invalid status transition
- **THEN** the system returns 400 Bad Request
- **AND** indicates valid transitions from current status

### Requirement: Proposal File Operations

The system SHALL provide endpoints to read and write proposal files.

#### Scenario: List proposal files

- **WHEN** a user calls `GET /api/v1/proposals/{id}/files`
- **THEN** the system returns list of files in draft_path
- **AND** includes file metadata (name, size, modified time)

#### Scenario: Read proposal file

- **WHEN** a user calls `GET /api/v1/proposals/{id}/files/{path}`
- **THEN** the system returns file content
- **AND** validates path is within proposal directory

#### Scenario: Write proposal file

- **WHEN** an Author calls `PUT /api/v1/proposals/{id}/files/{path}`
- **AND** proposal is in DRAFT status
- **THEN** the system creates backup of existing file
- **AND** writes new content
- **AND** logs modification to audit trail

#### Scenario: Write to non-draft proposal

- **WHEN** a user attempts to write to proposal not in DRAFT status
- **THEN** the system returns 400 Bad Request

### Requirement: Proposal Iteration

The system SHALL support LLM-assisted iteration on proposal content.

#### Scenario: Iterate with comments

- **WHEN** an Author calls `POST /api/v1/proposals/{id}/iterate`
- **WITH** user_instruction and selected comment IDs
- **THEN** the system reads current proposal files
- **AND** fetches selected review comments
- **AND** constructs meta-prompt with context
- **AND** calls LLM provider
- **AND** backs up existing files
- **AND** writes LLM output to proposal files
- **AND** automatically runs validation
- **AND** returns iteration result with validation status

#### Scenario: Iterate on locked project

- **WHEN** a user attempts iteration on locked project (locked by another user)
- **THEN** the system returns 409 Conflict

#### Scenario: Iterate LLM failure

- **WHEN** LLM call fails during iteration
- **THEN** the system returns 502 Bad Gateway
- **AND** does not modify any files
- **AND** logs the failure

### Requirement: File Backup Before Modification

The system SHALL create backups before overwriting proposal files.

#### Scenario: Backup created on iteration

- **WHEN** the system modifies a proposal file
- **THEN** a timestamped backup is created in `.backups/` subdirectory
- **AND** backup includes original filename and timestamp

#### Scenario: Restore from backup

- **WHEN** an Author calls `POST /api/v1/proposals/{id}/files/{path}/restore`
- **WITH** backup_id
- **THEN** the system restores file from specified backup
- **AND** creates backup of current version before restore
