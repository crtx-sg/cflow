# Validation Engine

## ADDED Requirements

### Requirement: OpenSpec CLI Wrapper

The system SHALL wrap OpenSpec CLI commands in a service class.

#### Scenario: Init project

- **WHEN** `OpenSpecClient.init_project(path, standard)` is called
- **THEN** the system executes `openspec init --standard {standard}` in specified path
- **AND** captures stdout and stderr
- **AND** returns structured result with success/failure status

#### Scenario: Scaffold change

- **WHEN** `OpenSpecClient.scaffold_change(path, name)` is called
- **THEN** the system executes `openspec scaffold {name}` in specified path
- **AND** returns the created directory path

#### Scenario: Validate change

- **WHEN** `OpenSpecClient.validate_change(path, name)` is called
- **THEN** the system executes `openspec validate {name} --strict` in specified path
- **AND** parses stdout for validation results
- **AND** returns structured validation report

### Requirement: Validation Execution

The system SHALL provide endpoint to trigger validation.

#### Scenario: Validate proposal

- **WHEN** a user calls `POST /api/v1/proposals/{id}/validate`
- **THEN** the system acquires project lock (or fails if locked)
- **AND** executes validation via OpenSpecClient
- **AND** stores validation result
- **AND** releases project lock
- **AND** returns validation report

#### Scenario: Validation already running

- **WHEN** validation is requested while another validation is in progress
- **THEN** the system returns 409 Conflict

### Requirement: Validation Result Parsing

The system SHALL parse CLI output into structured validation results.

#### Scenario: Parse success output

- **WHEN** validation CLI returns exit code 0
- **THEN** the system parses passed checks from stdout
- **AND** returns status "passed" with check details

#### Scenario: Parse failure output

- **WHEN** validation CLI returns non-zero exit code
- **THEN** the system parses errors and warnings from stdout/stderr
- **AND** categorizes issues (error, warning, info)
- **AND** returns status "failed" with issue details

#### Scenario: Parse traceability results

- **WHEN** validation includes traceability checks
- **THEN** the system extracts missing links, orphaned items
- **AND** includes in structured result

### Requirement: Validation History

The system SHALL maintain history of validation runs.

#### Scenario: Store validation result

- **WHEN** validation completes
- **THEN** the system stores result with timestamp, user, status, full output

#### Scenario: Query validation history

- **WHEN** a user calls `GET /api/v1/proposals/{id}/validations`
- **THEN** the system returns paginated validation history

#### Scenario: Get specific validation

- **WHEN** a user calls `GET /api/v1/validations/{id}`
- **THEN** the system returns full validation details including raw output

### Requirement: CLI Error Handling

The system SHALL handle CLI execution failures gracefully.

#### Scenario: CLI timeout

- **WHEN** CLI command exceeds timeout (default: 60 seconds)
- **THEN** the system kills the process
- **AND** returns error with partial output if available

#### Scenario: CLI not found

- **WHEN** `openspec` command is not available
- **THEN** the system returns 503 Service Unavailable
- **AND** logs the configuration issue

#### Scenario: Retry transient failure

- **WHEN** CLI fails due to transient error (file lock, resource exhaustion)
- **THEN** the system retries up to 3 times with exponential backoff

### Requirement: Path Security

The system SHALL validate all paths before CLI execution.

#### Scenario: Valid project path

- **WHEN** CLI operation is requested
- **THEN** the system validates path is within project directory
- **AND** path is canonicalized to prevent traversal

#### Scenario: Path traversal attempt

- **WHEN** path contains traversal sequences (../)
- **THEN** the system rejects the request with 400 Bad Request
- **AND** logs the security event

#### Scenario: Sanitize CLI arguments

- **WHEN** constructing CLI command
- **THEN** all arguments are sanitized to prevent injection
- **AND** shell metacharacters are escaped or rejected

### Requirement: Async Validation with Streaming

The system SHALL support async validation with streaming output.

#### Scenario: Start async validation

- **WHEN** a user calls `POST /api/v1/proposals/{id}/validate?async=true`
- **THEN** the system starts validation in background
- **AND** returns validation job ID immediately

#### Scenario: Stream validation output

- **WHEN** a user connects to `/ws/proposals/{id}/validate/{job_id}`
- **THEN** the system streams CLI output in real-time
- **AND** sends final status when complete

#### Scenario: Poll validation status

- **WHEN** a user calls `GET /api/v1/validations/{job_id}/status`
- **THEN** the system returns current status (running, completed, failed)
