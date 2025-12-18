# Proposal Lifecycle (Database-First)

## ADDED Requirements

### Requirement: Proposal CRUD Operations

The system SHALL provide endpoints to create, read, update, and delete change proposals with content stored in database.

#### Scenario: Create proposal

- **WHEN** an Author calls `POST /api/v1/projects/{project_id}/proposals` with name
- **THEN** the system creates proposal record with status DRAFT
- **AND** sets author_id to current user
- **AND** creates initial ProposalContent entries for standard files (proposal.md, tasks.md)
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
- **THEN** the system returns proposal details including status, author_id, filesystem_path

#### Scenario: Delete proposal

- **WHEN** the Author or Admin calls `DELETE /api/v1/proposals/{id}`
- **AND** proposal status is DRAFT
- **THEN** the system deletes proposal record and all ProposalContent
- **AND** logs deletion to audit trail

#### Scenario: Delete non-draft proposal

- **WHEN** a user attempts to delete proposal not in DRAFT status
- **THEN** the system returns 400 Bad Request

### Requirement: Proposal Status Workflow

The system SHALL enforce status transitions: DRAFT → REVIEW → READY → MERGED.

#### Scenario: Submit for review

- **WHEN** the Author calls `POST /api/v1/proposals/{id}/submit`
- **AND** proposal is in DRAFT status
- **AND** proposal has required content (proposal.md at minimum)
- **THEN** the system transitions status to REVIEW
- **AND** logs transition to audit trail

#### Scenario: Return to draft from review

- **WHEN** the Author calls `POST /api/v1/proposals/{id}/return-to-draft`
- **AND** proposal is in REVIEW status
- **THEN** the system transitions status to DRAFT
- **AND** logs transition to audit trail

#### Scenario: Mark ready with unresolved comments

- **WHEN** the Author calls `POST /api/v1/proposals/{id}/mark-ready`
- **AND** proposal has OPEN comments
- **THEN** the system returns 400 Bad Request
- **AND** includes list of unresolved comment IDs

#### Scenario: Mark ready success

- **WHEN** the Author calls `POST /api/v1/proposals/{id}/mark-ready`
- **AND** proposal is in REVIEW status
- **AND** all comments are resolved (ACCEPTED, REJECTED, or DEFERRED)
- **THEN** the system writes all ProposalContent to filesystem
- **AND** runs `openspec validate` on written files
- **AND** if validation passes, transitions status to READY
- **AND** sets filesystem_path to the written directory
- **AND** logs transition to audit trail

#### Scenario: Mark ready validation failure

- **WHEN** the system attempts to mark proposal ready
- **AND** `openspec validate` fails
- **THEN** the system deletes written files
- **AND** returns 400 Bad Request with validation errors
- **AND** proposal remains in REVIEW status

#### Scenario: Merge proposal

- **WHEN** an Admin calls `POST /api/v1/proposals/{id}/merge`
- **AND** proposal is in READY status
- **THEN** the system runs OpenSpec archive command
- **AND** transitions status to MERGED
- **AND** logs merge to audit trail

#### Scenario: Invalid status transition

- **WHEN** a user attempts invalid status transition
- **THEN** the system returns 400 Bad Request
- **AND** indicates valid transitions from current status

### Requirement: Database Content Storage

The system SHALL store proposal content in database during DRAFT and REVIEW states.

#### Scenario: Read content

- **WHEN** a user calls `GET /api/v1/proposals/{id}/content/{file_path}`
- **THEN** the system returns content from ProposalContent table
- **AND** includes version number and last updated info

#### Scenario: Write content in draft

- **WHEN** the Author calls `PUT /api/v1/proposals/{id}/content/{file_path}`
- **AND** proposal is in DRAFT status
- **THEN** the system saves content to ProposalContent table
- **AND** creates ContentVersion entry for history
- **AND** increments version number
- **AND** logs modification to audit trail

#### Scenario: Write content in review

- **WHEN** the Author calls `PUT /api/v1/proposals/{id}/content/{file_path}`
- **AND** proposal is in REVIEW status
- **THEN** the system saves content to ProposalContent table
- **AND** creates ContentVersion entry for history
- **AND** logs modification to audit trail

#### Scenario: Write content non-author

- **WHEN** a non-Author user attempts to write content
- **THEN** the system returns 403 Forbidden

#### Scenario: Write content in ready or merged

- **WHEN** any user attempts to write content to proposal in READY or MERGED status
- **THEN** the system returns 400 Bad Request

#### Scenario: List content files

- **WHEN** a user calls `GET /api/v1/proposals/{id}/content`
- **THEN** the system returns list of file paths with metadata
- **AND** includes version, size, updated_at for each file

### Requirement: Draft Proposal Input

The system SHALL provide a free-form text input for users to describe proposal requirements in DRAFT state.

#### Scenario: Submit proposal description

- **WHEN** the Author enters text in the proposal input textbox
- **AND** submits the input via `POST /api/v1/proposals/{id}/generate`
- **THEN** the system prepends "Create or Update OpenSpec proposal" to the user's input
- **AND** sends the combined prompt to the project's configured LLM
- **AND** saves the generated content to appropriate ProposalContent files (proposal.md, design.md, tasks.md)
- **AND** creates ContentVersion entries for each updated file
- **AND** logs the generation to audit trail

#### Scenario: Generate with existing content

- **WHEN** the Author submits input
- **AND** proposal already has content
- **THEN** the system includes existing content as context in the prompt
- **AND** the prompt becomes "Create or Update OpenSpec proposal" with user input and existing content
- **AND** LLM updates or refines the existing content based on new instructions

#### Scenario: Generate empty input

- **WHEN** the Author submits empty or whitespace-only input
- **THEN** the system returns 400 Bad Request
- **AND** indicates that input is required

#### Scenario: Generate streaming response

- **WHEN** the Author connects to `/ws/proposals/{id}/generate`
- **AND** sends input via WebSocket
- **THEN** the system streams LLM response in real-time
- **AND** sends completion status when finished

#### Scenario: Generate non-draft status

- **WHEN** a user attempts to generate content for proposal not in DRAFT status
- **THEN** the system returns 400 Bad Request
- **AND** indicates content generation only allowed in DRAFT state

### Requirement: Content Version History

The system SHALL maintain version history for all proposal content.

#### Scenario: Get version history

- **WHEN** a user calls `GET /api/v1/proposals/{id}/content/{file_path}/versions`
- **THEN** the system returns list of all versions
- **AND** includes version number, created_by, created_at, change_reason

#### Scenario: Get specific version

- **WHEN** a user calls `GET /api/v1/proposals/{id}/content/{file_path}/versions/{version}`
- **THEN** the system returns content for that specific version

#### Scenario: Rollback to version

- **WHEN** the Author calls `POST /api/v1/proposals/{id}/content/{file_path}/rollback`
- **WITH** version number
- **AND** proposal is in DRAFT or REVIEW status
- **THEN** the system restores content from specified version
- **AND** creates new version entry with reason "Rollback to version X"
- **AND** logs rollback to audit trail

### Requirement: Validate Draft

The system SHALL support validation of database content without writing to permanent filesystem.

#### Scenario: Validate draft success

- **WHEN** a user calls `POST /api/v1/proposals/{id}/validate-draft`
- **THEN** the system creates temporary directory
- **AND** writes all ProposalContent to temp directory structure
- **AND** executes `openspec validate` on temp directory
- **AND** parses and returns validation results
- **AND** deletes temporary directory
- **AND** stores validation result in database

#### Scenario: Validate draft failure

- **WHEN** validation finds errors
- **THEN** the system returns validation errors with file references
- **AND** categorizes issues (error, warning, info)
- **AND** proposal status is not changed

#### Scenario: Validate draft streaming

- **WHEN** a user connects to `/ws/proposals/{id}/validate-draft`
- **THEN** the system streams validation output in real-time
- **AND** sends final result when complete

### Requirement: Proposal Iteration

The system SHALL support LLM-assisted iteration on proposal content.

#### Scenario: Iterate with accepted comments

- **WHEN** the Author calls `POST /api/v1/proposals/{id}/iterate`
- **WITH** user_instruction and target file paths
- **THEN** the system reads current content from ProposalContent
- **AND** fetches comments with status ACCEPTED and selected_for_iteration=true
- **AND** constructs meta-prompt with context
- **AND** calls LLM provider
- **AND** saves generated content to ProposalContent (creates version)
- **AND** clears selected_for_iteration flag on processed comments
- **AND** automatically runs validate-draft
- **AND** returns iteration result with validation status

#### Scenario: Iterate non-author

- **WHEN** a non-Author user attempts iteration
- **THEN** the system returns 403 Forbidden

#### Scenario: Iterate LLM failure

- **WHEN** LLM call fails during iteration
- **THEN** the system returns 502 Bad Gateway
- **AND** does not modify any content
- **AND** logs the failure

### Requirement: Filesystem Write on Ready

The system SHALL write proposal content to filesystem only when transitioning to READY state.

#### Scenario: Write to filesystem

- **WHEN** proposal transitions to READY
- **THEN** the system creates directory `{project.local_path}/openspec/changes/{proposal.name}/`
- **AND** writes all ProposalContent files to appropriate paths
- **AND** validates path is within project root
- **AND** sets proposal.filesystem_path to the directory

#### Scenario: Filesystem write path validation

- **WHEN** writing to filesystem
- **THEN** all paths are validated against project root
- **AND** path traversal attempts are rejected

#### Scenario: Cleanup on validation failure

- **WHEN** filesystem write succeeds but validation fails
- **THEN** the system deletes all written files
- **AND** returns proposal to REVIEW status
- **AND** filesystem_path remains NULL
