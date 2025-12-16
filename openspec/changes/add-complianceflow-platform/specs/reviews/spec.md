# Review System

## ADDED Requirements

### Requirement: Review Comment CRUD

The system SHALL provide endpoints to create, read, update, and delete review comments.

#### Scenario: Create comment

- **WHEN** a Reviewer calls `POST /api/v1/proposals/{proposal_id}/comments`
- **WITH** target_file, line_number (optional), comment_text
- **AND** proposal is in REVIEW status
- **THEN** the system creates comment with status OPEN
- **AND** logs creation to audit trail

#### Scenario: Create comment on non-review proposal

- **WHEN** a user creates comment on proposal not in REVIEW status
- **THEN** the system returns 400 Bad Request

#### Scenario: List comments

- **WHEN** a user calls `GET /api/v1/proposals/{proposal_id}/comments`
- **THEN** the system returns all comments grouped by target_file
- **AND** includes status and author_response for each comment

#### Scenario: Update comment

- **WHEN** comment author calls `PUT /api/v1/comments/{id}`
- **AND** comment status is OPEN
- **THEN** the system updates comment_text
- **AND** logs update to audit trail

#### Scenario: Update resolved comment

- **WHEN** comment author attempts to update comment not in OPEN status
- **THEN** the system returns 400 Bad Request

#### Scenario: Delete comment

- **WHEN** comment author or Admin calls `DELETE /api/v1/comments/{id}`
- **AND** comment status is OPEN
- **THEN** the system deletes the comment
- **AND** logs deletion to audit trail

### Requirement: Comment Status Workflow

The system SHALL track comment resolution with status: OPEN, ACCEPTED, REJECTED, DEFERRED.

#### Scenario: Accept comment

- **WHEN** proposal Author calls `POST /api/v1/comments/{id}/accept`
- **WITH** author_response (optional reasoning)
- **AND** comment status is OPEN
- **THEN** the system sets status to ACCEPTED
- **AND** sets resolved_at to current timestamp
- **AND** stores author_response
- **AND** logs resolution to audit trail

#### Scenario: Reject comment

- **WHEN** proposal Author calls `POST /api/v1/comments/{id}/reject`
- **WITH** author_response (required reasoning)
- **AND** comment status is OPEN
- **THEN** the system sets status to REJECTED
- **AND** sets resolved_at to current timestamp
- **AND** stores author_response
- **AND** logs resolution to audit trail

#### Scenario: Reject without reason

- **WHEN** proposal Author attempts to reject without author_response
- **THEN** the system returns 400 Bad Request
- **AND** indicates reason is required for rejection

#### Scenario: Defer comment

- **WHEN** proposal Author calls `POST /api/v1/comments/{id}/defer`
- **WITH** author_response (required reasoning)
- **AND** comment status is OPEN
- **THEN** the system sets status to DEFERRED
- **AND** sets resolved_at to current timestamp
- **AND** stores author_response
- **AND** logs resolution to audit trail

#### Scenario: Reopen comment

- **WHEN** comment author calls `POST /api/v1/comments/{id}/reopen`
- **AND** comment status is ACCEPTED, REJECTED, or DEFERRED
- **THEN** the system sets status to OPEN
- **AND** clears resolved_at
- **AND** logs reopening to audit trail

#### Scenario: Non-author resolve attempt

- **WHEN** a user other than proposal Author attempts to resolve a comment
- **THEN** the system returns 403 Forbidden

### Requirement: Comment Selection for Iteration

The system SHALL support selecting accepted comments to include in LLM iteration context.

#### Scenario: Select comment for iteration

- **WHEN** the proposal Author calls `POST /api/v1/comments/{id}/select`
- **AND** comment status is ACCEPTED
- **THEN** the system sets selected_for_iteration to true

#### Scenario: Select non-accepted comment

- **WHEN** the proposal Author attempts to select comment not in ACCEPTED status
- **THEN** the system returns 400 Bad Request
- **AND** indicates only accepted comments can be selected

#### Scenario: Deselect comment

- **WHEN** the proposal Author calls `DELETE /api/v1/comments/{id}/select`
- **THEN** the system sets selected_for_iteration to false

#### Scenario: Batch select comments

- **WHEN** the proposal Author calls `POST /api/v1/proposals/{id}/comments/select`
- **WITH** list of comment IDs
- **THEN** the system validates all comments are ACCEPTED
- **AND** sets selected_for_iteration for all specified comments

#### Scenario: Clear selection after iteration

- **WHEN** a proposal iteration completes successfully
- **THEN** the system clears selected_for_iteration for all processed comments

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

- **WHEN** an Admin or proposal Author calls `POST /api/v1/proposals/{id}/reviewers`
- **WITH** user_id
- **THEN** the system assigns user as reviewer
- **AND** logs assignment to audit trail

#### Scenario: Remove reviewer

- **WHEN** an Admin or proposal Author calls `DELETE /api/v1/proposals/{id}/reviewers/{user_id}`
- **THEN** the system removes reviewer assignment
- **AND** logs removal to audit trail

#### Scenario: List reviewers

- **WHEN** a user calls `GET /api/v1/proposals/{id}/reviewers`
- **THEN** the system returns list of assigned reviewers

### Requirement: Ready Transition Guard

The system SHALL prevent transition to READY state with unresolved comments.

#### Scenario: Check unresolved comments

- **WHEN** Author attempts to mark proposal as READY
- **AND** there are comments with status OPEN
- **THEN** the system returns 400 Bad Request
- **AND** includes count and IDs of unresolved comments

#### Scenario: Allow ready with all resolved

- **WHEN** Author attempts to mark proposal as READY
- **AND** all comments have status ACCEPTED, REJECTED, or DEFERRED
- **THEN** the system allows the transition

### Requirement: Comment Statistics

The system SHALL provide comment statistics for proposals.

#### Scenario: Get comment statistics

- **WHEN** a user calls `GET /api/v1/proposals/{id}/comments/stats`
- **THEN** the system returns counts by status (OPEN, ACCEPTED, REJECTED, DEFERRED)
- **AND** includes count of selected_for_iteration
