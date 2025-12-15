# Review System

## ADDED Requirements

### Requirement: Review Comment CRUD

The system SHALL provide endpoints to create, read, update, and delete review comments.

#### Scenario: Create comment

- **WHEN** a Reviewer calls `POST /api/v1/proposals/{proposal_id}/comments`
- **WITH** target_file, line_number (optional), comment_text
- **THEN** the system creates comment with status OPEN
- **AND** logs creation to audit trail

#### Scenario: Create comment on non-review proposal

- **WHEN** a user creates comment on proposal not in REVIEW status
- **THEN** the system returns 400 Bad Request

#### Scenario: List comments

- **WHEN** a user calls `GET /api/v1/proposals/{proposal_id}/comments`
- **THEN** the system returns all comments grouped by target_file

#### Scenario: Update comment

- **WHEN** comment author calls `PUT /api/v1/comments/{id}`
- **THEN** the system updates comment_text
- **AND** logs update to audit trail

#### Scenario: Delete comment

- **WHEN** comment author or Admin calls `DELETE /api/v1/comments/{id}`
- **THEN** the system deletes the comment
- **AND** logs deletion to audit trail

### Requirement: Comment Status Workflow

The system SHALL track comment resolution status.

#### Scenario: Resolve comment

- **WHEN** proposal Author calls `POST /api/v1/comments/{id}/resolve`
- **THEN** the system sets status to RESOLVED
- **AND** logs resolution to audit trail

#### Scenario: Reopen comment

- **WHEN** comment author calls `POST /api/v1/comments/{id}/reopen`
- **THEN** the system sets status to OPEN
- **AND** logs reopening to audit trail

### Requirement: Comment Selection for Iteration

The system SHALL support selecting comments to include in LLM iteration context.

#### Scenario: Select comment for iteration

- **WHEN** an Author calls `POST /api/v1/comments/{id}/select`
- **THEN** the system sets selected_for_iteration to true

#### Scenario: Deselect comment

- **WHEN** an Author calls `DELETE /api/v1/comments/{id}/select`
- **THEN** the system sets selected_for_iteration to false

#### Scenario: Batch select comments

- **WHEN** an Author calls `POST /api/v1/proposals/{id}/comments/select`
- **WITH** list of comment IDs
- **THEN** the system sets selected_for_iteration for all specified comments

#### Scenario: Clear selection after iteration

- **WHEN** a proposal iteration completes
- **THEN** the system clears selected_for_iteration for all comments
- **AND** resolves comments that were selected

### Requirement: Comment Threading

The system SHALL support threaded replies to comments.

#### Scenario: Reply to comment

- **WHEN** a user calls `POST /api/v1/comments/{id}/replies`
- **WITH** comment_text
- **THEN** the system creates reply linked to parent comment

#### Scenario: List comment thread

- **WHEN** a user calls `GET /api/v1/comments/{id}`
- **THEN** the response includes all replies in chronological order

### Requirement: Reviewer Assignment

The system SHALL support assigning reviewers to proposals.

#### Scenario: Assign reviewer

- **WHEN** an Admin or Author calls `POST /api/v1/proposals/{id}/reviewers`
- **WITH** user_id
- **THEN** the system assigns user as reviewer
- **AND** logs assignment to audit trail

#### Scenario: Remove reviewer

- **WHEN** an Admin or Author calls `DELETE /api/v1/proposals/{id}/reviewers/{user_id}`
- **THEN** the system removes reviewer assignment
- **AND** logs removal to audit trail

#### Scenario: List reviewers

- **WHEN** a user calls `GET /api/v1/proposals/{id}/reviewers`
- **THEN** the system returns list of assigned reviewers
