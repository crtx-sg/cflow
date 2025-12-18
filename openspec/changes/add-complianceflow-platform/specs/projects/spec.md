# Project Management

## ADDED Requirements

### Requirement: Project CRUD Operations

The system SHALL provide endpoints to create, read, update, and delete projects.

#### Scenario: Create project

- **WHEN** an Author calls `POST /api/v1/projects` with name, local_path, compliance_standard, and optional openspec_tool
- **THEN** the system creates project record
- **AND** validates the local_path exists and is accessible
- **AND** reads the `.env` file in local_path for OPENSPEC_TOOL configuration (if not provided in request)
- **AND** runs `openspec init --tools {openspec_tool}` in the directory
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
- **THEN** the system returns project details including compliance standard

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

### Requirement: Project Permissions

The system SHALL enforce project-level access control.

#### Scenario: Owner full access

- **WHEN** project owner accesses project endpoints
- **THEN** the system grants full access

#### Scenario: Assigned user access

- **WHEN** a user is assigned to a project with a role
- **THEN** the system grants access according to role permissions

#### Scenario: Unassigned user denied

- **WHEN** a user not assigned to project attempts access
- **AND** user is not Admin
- **THEN** the system returns 403 Forbidden

#### Scenario: Admin override

- **WHEN** an Admin accesses any project
- **THEN** the system grants full access

### Requirement: Project Statistics

The system SHALL provide project statistics endpoint.

#### Scenario: Get project statistics

- **WHEN** a user calls `GET /api/v1/projects/{id}/stats`
- **THEN** the system returns proposal counts by status
- **AND** includes recent activity summary

### Requirement: OpenSpec Tool Configuration

The system SHALL support per-project OpenSpec tool configuration.

#### Scenario: Tool configured via project .env

- **WHEN** a project directory contains a `.env` file with `OPENSPEC_TOOL=<tool_name>`
- **THEN** the system uses that tool for `openspec init --tools <tool_name>`
- **AND** associates the project with the corresponding LLM backend

#### Scenario: Tool specified in API request

- **WHEN** a project is created with `openspec_tool` parameter in the request body
- **THEN** the system uses the specified tool instead of reading from `.env`
- **AND** stores the tool configuration in the project record

#### Scenario: Default tool when not configured

- **WHEN** neither `.env` nor API request specifies a tool
- **THEN** the system uses `none` as the default tool
- **AND** uses the global LLM configuration for the project

#### Scenario: Supported tools

- **WHEN** a tool is specified
- **THEN** the system validates it against supported tools: claude, cursor, github-copilot, windsurf, cline, amazon-q, gemini, opencode, qoder, roocode, or none
- **AND** returns 400 Bad Request for unsupported tools
