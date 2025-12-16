# Change: Add ComplianceFlow Platform

## Why

Organizations developing safety-critical software (medical devices, automotive, aerospace) must comply with standards like IEC 62304, ISO 26262, and DO-178C. These standards require rigorous documentation, traceability, and audit trails. Currently, teams manually manage compliance artifacts using the OpenSpec CLI, which is error-prone and lacks visibility.

ComplianceFlow provides a GUI and logic wrapper around the OpenSpec CLI tool, enabling teams to draft, validate, iterate, and implement compliance proposals through an intuitive web interface with LLM-assisted content generation.

## What Changes

### Core Platform
- **BREAKING**: New greenfield application with React frontend and FastAPI backend
- Initialize projects via `openspec init` with compliance standard selection
- SQLite database (SQLModel) with Postgres migration path
- Project-based multi-tenancy

### Authentication & Authorization (Gap: High Risk)
- JWT-based authentication with refresh token rotation
- Role-Based Access Control (RBAC): Admin, Reviewer, Author, Viewer
- API security: rate limiting, CORS configuration, input validation
- Session management with configurable expiry

### Project Management
- Create/configure projects linked to local filesystem paths
- Validate `openspec.json` schema on project creation
- Project-level permission assignments
- No filesystem locking required (database-first approach)

### Proposal Lifecycle (Database-First Workflow)
- **DRAFT state**: Content stored in database only, not filesystem
  - Only Author can edit proposal content
  - All changes tracked with version history in database
  - "Validate Draft" action writes to temp dir for CLI validation
- **REVIEW state**: Content remains in database
  - Reviewers can view and add comments
  - Author manages comment status: ACCEPTED, REJECTED, DEFERRED
  - Author selects accepted comments for LLM iteration
  - Iteration updates database content, stays in REVIEW
- **READY state**: Content written to filesystem
  - User action "Mark Ready" triggers filesystem write
  - Writes to `openspec/changes/<proposal>/` directory
  - OpenSpec CLI validation runs; failure returns to REVIEW
- **MERGED state**: Archived via OpenSpec CLI
- Status workflow: DRAFT → REVIEW → READY → MERGED
- LLM-powered content generation for proposal files

### LLM Integration (Gap: High Risk)
- Provider-agnostic abstraction layer (OpenAI, Anthropic, local models)
- Local LLM support: Ollama, vLLM (for air-gapped deployments)
- Secure API key management (encrypted storage, environment variables)
- Token usage tracking and cost controls
- Configurable rate limits and fallback strategies

### Validation Engine
- Execute `openspec validate <proposal_name>` and parse results
- "Validate Draft" endpoint: temp filesystem write → validate → cleanup
- Display validation errors/warnings in terminal-like UI console
- Auto-validate after LLM iterations (on temp files)
- Retry strategies for CLI failures (Gap: Medium Risk)

### Review System
- Comment threads on specific files/lines (stored in database)
- Comment status workflow: OPEN → ACCEPTED/REJECTED/DEFERRED
- Author provides response/reason for each comment resolution
- Select accepted comments for LLM iteration context
- State transition guard: all OPEN comments must be resolved before READY

### Real-time Updates (Gap: Medium Risk)
- WebSocket support for streaming CLI output
- Progress indicators for long-running operations
- Live validation status updates

### File System Security (Gap: High Risk)
- Path traversal protection for filesystem write operations (READY state only)
- Sandboxed subprocess execution for OpenSpec CLI
- Allowlist-based directory access
- Input sanitization for CLI arguments

### Content Versioning
- All proposal content changes tracked in database
- Version history with author, timestamp, change reason
- Rollback to any previous version
- No manual file backup required (database handles versioning)

### Audit Trail (Gap: Medium Risk)
- Log all state transitions, approvals, and content modifications
- Configurable retention policy
- Export capabilities for compliance audits
- Immutable audit records

## Impact

### Affected Specs (New Capabilities)
- `specs/core/` - Platform configuration and initialization
- `specs/auth/` - Authentication and authorization
- `specs/projects/` - Project management
- `specs/proposals/` - Proposal lifecycle (database-first)
- `specs/reviews/` - Review and commenting system
- `specs/llm-integration/` - LLM abstraction layer
- `specs/validation/` - OpenSpec CLI integration
- `specs/realtime/` - WebSocket and streaming

### Affected Code
- `backend/` - FastAPI application (new)
- `frontend/` - React/Vite application (new)
- `database/` - SQLModel schemas and migrations (new)

### Dependencies
- OpenSpec CLI (`pip install openspec`)
- Python 3.11+, Node.js 20+
- SQLite (dev), PostgreSQL (prod)

### Risks
| Risk | Mitigation |
|------|------------|
| OpenSpec CLI command changes | Version pinning, integration tests |
| LLM API availability | Fallback providers, graceful degradation |
| Large content in database | TEXT columns, acceptable for SQLite/Postgres |
| Validation failure at READY | "Validate Draft" action catches errors early |
| Path traversal attacks | Strict validation on READY write, sandboxing |
