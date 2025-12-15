# Authentication & Authorization

## ADDED Requirements

### Requirement: JWT Access Token Authentication

The system SHALL authenticate users using JWT access tokens with 15-minute expiry.

#### Scenario: Valid token accepted

- **WHEN** a client provides valid JWT in Authorization header
- **THEN** the system extracts user identity and processes the request

#### Scenario: Expired token rejected

- **WHEN** a client provides expired JWT
- **THEN** the system returns 401 Unauthorized
- **AND** includes error code `token_expired`

#### Scenario: Invalid token rejected

- **WHEN** a client provides malformed or tampered JWT
- **THEN** the system returns 401 Unauthorized
- **AND** includes error code `token_invalid`

### Requirement: Refresh Token Rotation

The system SHALL issue HTTP-only refresh tokens with 7-day expiry and rotation on use.

#### Scenario: Token refresh success

- **WHEN** a client calls `POST /api/v1/auth/refresh` with valid refresh token
- **THEN** the system issues new access token
- **AND** issues new refresh token (rotation)
- **AND** invalidates the old refresh token

#### Scenario: Refresh token reuse detected

- **WHEN** a client attempts to use an already-rotated refresh token
- **THEN** the system revokes all tokens for that user
- **AND** returns 401 Unauthorized with `token_reuse_detected`

### Requirement: User Login

The system SHALL authenticate users with email and password.

#### Scenario: Login success

- **WHEN** a user provides valid email and password to `POST /api/v1/auth/login`
- **THEN** the system returns access token in response body
- **AND** sets refresh token in HTTP-only cookie
- **AND** logs the login event to audit trail

#### Scenario: Login invalid credentials

- **WHEN** a user provides invalid email or password
- **THEN** the system returns 401 Unauthorized
- **AND** does not reveal whether email or password was incorrect

#### Scenario: Login rate limited

- **WHEN** a user exceeds 5 failed login attempts in 15 minutes
- **THEN** the system temporarily blocks login for that email
- **AND** returns 429 Too Many Requests

### Requirement: User Logout

The system SHALL invalidate tokens on logout.

#### Scenario: Logout success

- **WHEN** a user calls `POST /api/v1/auth/logout`
- **THEN** the system invalidates the refresh token
- **AND** clears the refresh token cookie
- **AND** logs the logout event to audit trail

### Requirement: Password Security

The system SHALL hash passwords using bcrypt with cost factor 12.

#### Scenario: Password stored securely

- **WHEN** a user account is created
- **THEN** the password is hashed with bcrypt before storage
- **AND** the plaintext password is never stored or logged

### Requirement: Role-Based Access Control

The system SHALL enforce RBAC with roles: Admin, Reviewer, Author, Viewer.

#### Scenario: Admin full access

- **WHEN** an Admin user accesses any endpoint
- **THEN** the system grants access

#### Scenario: Reviewer proposal access

- **WHEN** a Reviewer user accesses proposal review endpoints
- **THEN** the system grants read and comment access
- **AND** denies proposal creation and deletion

#### Scenario: Author proposal management

- **WHEN** an Author user accesses proposal endpoints
- **THEN** the system grants create, read, update access for own proposals
- **AND** denies access to other users' proposals unless shared

#### Scenario: Viewer read-only access

- **WHEN** a Viewer user accesses any endpoint
- **THEN** the system grants read-only access
- **AND** denies all write operations

#### Scenario: Insufficient permissions

- **WHEN** a user attempts an action beyond their role
- **THEN** the system returns 403 Forbidden
- **AND** logs the access attempt to audit trail
