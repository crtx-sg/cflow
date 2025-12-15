# Real-time Updates

## ADDED Requirements

### Requirement: WebSocket Connection Management

The system SHALL provide WebSocket endpoints for real-time communication.

#### Scenario: Establish WebSocket connection

- **WHEN** a client connects to `/ws/projects/{project_id}`
- **WITH** valid JWT token
- **THEN** the system establishes WebSocket connection
- **AND** associates connection with user and project

#### Scenario: WebSocket authentication

- **WHEN** a client connects without valid token
- **THEN** the system closes connection with 4001 Unauthorized

#### Scenario: Connection heartbeat

- **WHEN** WebSocket connection is established
- **THEN** the system sends ping every 30 seconds
- **AND** expects pong within 10 seconds
- **AND** closes connection on timeout

#### Scenario: Reconnection handling

- **WHEN** a client reconnects after disconnect
- **THEN** the system resumes from last known state
- **AND** sends missed events if buffered

### Requirement: Validation Streaming

The system SHALL stream validation output via WebSocket.

#### Scenario: Stream validation start

- **WHEN** validation begins
- **THEN** the system sends `{"type": "validation_start", "proposal_id": id}`

#### Scenario: Stream validation output

- **WHEN** CLI produces output
- **THEN** the system sends `{"type": "output", "line": content, "stream": "stdout|stderr"}`

#### Scenario: Stream validation complete

- **WHEN** validation completes
- **THEN** the system sends `{"type": "validation_complete", "status": "passed|failed", "summary": {...}}`

#### Scenario: Stream validation error

- **WHEN** validation fails unexpectedly
- **THEN** the system sends `{"type": "validation_error", "error": message}`

### Requirement: LLM Streaming

The system SHALL stream LLM responses via WebSocket.

#### Scenario: Stream iteration start

- **WHEN** LLM iteration begins
- **THEN** the system sends `{"type": "iteration_start", "proposal_id": id}`

#### Scenario: Stream LLM tokens

- **WHEN** LLM generates tokens
- **THEN** the system sends `{"type": "token", "content": token_text}`

#### Scenario: Stream iteration complete

- **WHEN** LLM iteration completes
- **THEN** the system sends `{"type": "iteration_complete", "files_modified": [...], "validation": {...}}`

#### Scenario: Stream iteration cancelled

- **WHEN** user cancels iteration
- **THEN** the system cancels LLM request
- **AND** sends `{"type": "iteration_cancelled"}`

### Requirement: Server-Sent Events Fallback

The system SHALL provide SSE endpoints as WebSocket fallback.

#### Scenario: SSE connection

- **WHEN** a client requests `/api/v1/proposals/{id}/events`
- **WITH** Accept: text/event-stream
- **THEN** the system establishes SSE connection

#### Scenario: SSE validation events

- **WHEN** validation events occur
- **THEN** events are sent in SSE format
- **AND** include event type and JSON data

#### Scenario: SSE reconnection

- **WHEN** SSE connection drops
- **AND** client reconnects with Last-Event-ID
- **THEN** the system resumes from that event ID

### Requirement: Event Broadcasting

The system SHALL broadcast events to relevant connected clients.

#### Scenario: Proposal status change

- **WHEN** proposal status changes
- **THEN** the system broadcasts to all clients viewing that proposal

#### Scenario: New comment notification

- **WHEN** a new comment is created
- **THEN** the system broadcasts to proposal reviewers and author

#### Scenario: Lock status change

- **WHEN** project lock status changes
- **THEN** the system broadcasts to all clients in that project

### Requirement: Connection Limits

The system SHALL enforce connection limits for resource management.

#### Scenario: Max connections per user

- **WHEN** user exceeds max WebSocket connections (default: 5)
- **THEN** the oldest connection is closed
- **AND** new connection is accepted

#### Scenario: Max connections per project

- **WHEN** project exceeds max concurrent connections (default: 50)
- **THEN** new connection is rejected with 503 Service Unavailable

### Requirement: Audit Trail

The system SHALL provide real-time audit events.

#### Scenario: Subscribe to audit events

- **WHEN** an Admin connects to `/ws/audit`
- **THEN** the system streams audit events in real-time

#### Scenario: Filter audit events

- **WHEN** audit subscription includes filters
- **THEN** only matching events are streamed
