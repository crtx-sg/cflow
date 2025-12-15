# Core Platform

## ADDED Requirements

### Requirement: Platform Configuration

The system SHALL provide configuration via environment variables and `openspec.json` schema.

#### Scenario: Environment configuration loaded

- **WHEN** the application starts
- **THEN** configuration is loaded from environment variables
- **AND** defaults are applied for missing optional values

#### Scenario: OpenSpec JSON schema validation

- **WHEN** a project is created or loaded
- **THEN** the system validates `openspec.json` against the schema
- **AND** rejects invalid configurations with descriptive errors

### Requirement: API Versioning

The system SHALL version all API endpoints using URL path prefix `/api/v1/`.

#### Scenario: Versioned API endpoint

- **WHEN** a client requests `/api/v1/projects`
- **THEN** the v1 API handler processes the request

#### Scenario: Unversioned API rejected

- **WHEN** a client requests `/api/projects` (without version)
- **THEN** the system returns 404 Not Found

### Requirement: Health Check Endpoint

The system SHALL provide a health check endpoint for monitoring.

#### Scenario: Health check success

- **WHEN** a client requests `GET /health`
- **THEN** the system returns 200 OK with service status
- **AND** includes database connectivity status
- **AND** includes OpenSpec CLI availability status

### Requirement: Rate Limiting

The system SHALL enforce rate limits on API endpoints to prevent abuse.

#### Scenario: Rate limit exceeded

- **WHEN** a client exceeds the configured request limit (default: 100/minute)
- **THEN** the system returns 429 Too Many Requests
- **AND** includes `Retry-After` header

#### Scenario: Rate limit headers included

- **WHEN** a client makes an API request
- **THEN** the response includes `X-RateLimit-Remaining` header

### Requirement: CORS Configuration

The system SHALL configure CORS to allow requests from authorized frontend origins.

#### Scenario: CORS preflight success

- **WHEN** a browser sends OPTIONS preflight request from allowed origin
- **THEN** the system returns appropriate CORS headers
- **AND** allows the subsequent request

#### Scenario: CORS unauthorized origin

- **WHEN** a browser sends request from unauthorized origin
- **THEN** the system rejects the request with CORS error
