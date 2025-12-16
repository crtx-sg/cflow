# Tasks: ComplianceFlow Platform

## 1. Project Setup

- [ ] 1.1 Initialize monorepo structure (`backend/`, `frontend/`)
- [ ] 1.2 Set up Python backend with FastAPI, SQLModel, uvicorn
- [ ] 1.3 Set up React frontend with Vite, TailwindCSS, React Flow
- [ ] 1.4 Configure ESLint, Prettier, Ruff for code quality
- [ ] 1.5 Create Docker Compose for local development
- [ ] 1.6 Set up environment configuration (.env.example)

## 2. Database Layer

- [ ] 2.1 Define SQLModel schemas: User, Project, ChangeProposal
- [ ] 2.2 Define ProposalContent table for storing file contents
- [ ] 2.3 Define ContentVersion table for version history
- [ ] 2.4 Define ReviewComment table with status enum (OPEN, ACCEPTED, REJECTED, DEFERRED)
- [ ] 2.5 Define AuditLog table for immutable audit records
- [ ] 2.6 Set up Alembic migrations
- [ ] 2.7 Create database initialization script
- [ ] 2.8 Add SQLite connection with Postgres migration path

## 3. Authentication & Authorization

- [ ] 3.1 Implement JWT access token generation (15min expiry)
- [ ] 3.2 Implement HTTP-only refresh token rotation (7d expiry)
- [ ] 3.3 Create auth endpoints: `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`
- [ ] 3.4 Implement password hashing with bcrypt
- [ ] 3.5 Define RBAC roles: Admin, Reviewer, Author, Viewer
- [ ] 3.6 Create permission decorators for route protection
- [ ] 3.7 Add rate limiting middleware (slowapi)
- [ ] 3.8 Configure CORS for frontend origin

## 4. OpenSpec CLI Integration

- [ ] 4.1 Create `OpenSpecClient` service class
- [ ] 4.2 Implement `init_project(path, standard)` - runs `openspec init`
- [ ] 4.3 Implement `validate_change(path, proposal_name)` - runs `openspec validate --strict`
- [ ] 4.4 Implement CLI output parsing (stdout/stderr capture)
- [ ] 4.5 Add retry logic with exponential backoff for transient failures
- [ ] 4.6 Implement async subprocess execution for streaming output

## 5. File System Security

- [ ] 5.1 Implement path validation against project allowlist
- [ ] 5.2 Create `validate_path()` utility with canonicalization
- [ ] 5.3 Sanitize CLI arguments to prevent injection
- [ ] 5.4 Add project directory existence validation

## 6. Project Management

- [ ] 6.1 Create project CRUD endpoints (`/api/v1/projects`)
- [ ] 6.2 Implement `openspec.json` schema validation
- [ ] 6.3 Implement project ownership and permission assignment
- [ ] 6.4 Create project initialization flow (calls `openspec init`)

## 7. Content Versioning Service

- [ ] 7.1 Create ContentVersioningService class
- [ ] 7.2 Implement `save_content(proposal_id, file_path, content, user_id, reason)`
- [ ] 7.3 Implement `get_content(proposal_id, file_path)` - returns current content
- [ ] 7.4 Implement `get_version_history(proposal_id, file_path)` - returns all versions
- [ ] 7.5 Implement `rollback_to_version(proposal_id, file_path, version_id)`
- [ ] 7.6 Add automatic version creation on each content update

## 8. Proposal Lifecycle (Database-First)

- [ ] 8.1 Create proposal CRUD endpoints (`/api/v1/proposals`)
- [ ] 8.2 Implement proposal creation with DRAFT status
- [ ] 8.3 Implement Author-only edit permission in DRAFT state
- [ ] 8.4 Create content endpoints: GET/PUT `/api/v1/proposals/{id}/content/{file_path}`
- [ ] 8.5 Implement status workflow: DRAFT → REVIEW → READY → MERGED
- [ ] 8.6 Add status transition validation
- [ ] 8.7 Implement proposal search/filter with pagination

## 9. Validate Draft Feature

- [ ] 9.1 Create "Validate Draft" endpoint (`POST /api/v1/proposals/{id}/validate-draft`)
- [ ] 9.2 Implement temp directory creation with proposal content
- [ ] 9.3 Write all ProposalContent to temp filesystem structure
- [ ] 9.4 Execute `openspec validate` on temp directory
- [ ] 9.5 Parse and return validation results
- [ ] 9.6 Auto-cleanup temp directory after validation
- [ ] 9.7 Store validation result in database

## 10. Mark Ready Feature (Filesystem Write)

- [ ] 10.1 Create "Mark Ready" endpoint (`POST /api/v1/proposals/{id}/mark-ready`)
- [ ] 10.2 Validate all OPEN comments are resolved before transition
- [ ] 10.3 Write all ProposalContent to project filesystem (`openspec/changes/<name>/`)
- [ ] 10.4 Execute `openspec validate` on written files
- [ ] 10.5 If validation fails, delete written files and return to REVIEW
- [ ] 10.6 If validation passes, update status to READY
- [ ] 10.7 Set filesystem_path on proposal record
- [ ] 10.8 Log transition to audit trail

## 11. LLM Integration

- [ ] 11.1 Define `LLMProvider` protocol interface
- [ ] 11.2 Implement OpenAI provider
- [ ] 11.3 Implement Anthropic provider
- [ ] 11.4 Implement Ollama provider (local)
- [ ] 11.5 Implement vLLM provider (local)
- [ ] 11.6 Create provider factory with configuration
- [ ] 11.7 Implement fallback chain logic
- [ ] 11.8 Add token usage tracking
- [ ] 11.9 Secure API key storage (encrypted config or env vars)

## 12. Iteration Engine

- [ ] 12.1 Create iteration endpoint (`POST /api/v1/proposals/{id}/iterate`)
- [ ] 12.2 Validate only Author can trigger iteration
- [ ] 12.3 Fetch selected (ACCEPTED) comments for context
- [ ] 12.4 Implement meta-prompt construction with context, draft, comments
- [ ] 12.5 Call LLM provider for content generation
- [ ] 12.6 Save generated content to ProposalContent (creates version)
- [ ] 12.7 Auto-trigger "Validate Draft" after iteration
- [ ] 12.8 Return iteration result with validation status

## 13. Review System

- [ ] 13.1 Create review comment CRUD endpoints (`/api/v1/proposals/{id}/comments`)
- [ ] 13.2 Implement comment creation (Reviewers only, REVIEW state only)
- [ ] 13.3 Implement comment status workflow: OPEN → ACCEPTED/REJECTED/DEFERRED
- [ ] 13.4 Add author_response field for resolution reasoning
- [ ] 13.5 Create status update endpoint (`POST /api/v1/comments/{id}/resolve`)
- [ ] 13.6 Implement comment selection for iteration (`selected_for_iteration` flag)
- [ ] 13.7 Add transition guard: all OPEN comments must be resolved before READY
- [ ] 13.8 Implement comment threading (replies)

## 14. Real-time Updates

- [ ] 14.1 Set up WebSocket endpoint (`/ws/proposals/{id}/validate`)
- [ ] 14.2 Stream CLI output in real-time during validation
- [ ] 14.3 Implement SSE fallback endpoint
- [ ] 14.4 Add WebSocket connection management (ping/pong, reconnect)
- [ ] 14.5 Create LLM streaming endpoint (`/ws/proposals/{id}/iterate`)

## 15. Audit System

- [ ] 15.1 Implement audit logging service
- [ ] 15.2 Log all state transitions (DRAFT→REVIEW→READY→MERGED)
- [ ] 15.3 Log all content modifications with version reference
- [ ] 15.4 Log comment resolutions with author reasoning
- [ ] 15.5 Add audit log query endpoint with filters
- [ ] 15.6 Implement audit export (CSV, JSON)
- [ ] 15.7 Configure retention policy settings

## 16. Frontend - Core

- [ ] 16.1 Set up React Router with protected routes
- [ ] 16.2 Implement auth context and token management
- [ ] 16.3 Create API client with interceptors (auth, error handling)
- [ ] 16.4 Build login/logout pages
- [ ] 16.5 Create main layout with navigation

## 17. Frontend - Project Management

- [ ] 17.1 Build project list dashboard
- [ ] 17.2 Create project wizard (name, standard, directory path)
- [ ] 17.3 Implement project settings page

## 18. Frontend - Proposal Management

- [ ] 18.1 Build proposal list view with pagination and filters
- [ ] 18.2 Create proposal creation form
- [ ] 18.3 Build proposal detail view with status badge
- [ ] 18.4 Implement status transition controls (Submit for Review, Mark Ready)
- [ ] 18.5 Add proposal file browser (tree view from database content)

## 19. Frontend - Editor & Review

- [ ] 19.1 Build markdown editor for proposal files (edits database content)
- [ ] 19.2 Implement diff view for content versions
- [ ] 19.3 Create comment sidebar with threading
- [ ] 19.4 Build comment status controls (Accept, Reject, Defer with reason)
- [ ] 19.5 Add comment selection for iteration
- [ ] 19.6 Build iteration trigger with instruction input
- [ ] 19.7 Implement version history panel with rollback

## 20. Frontend - Validation Console

- [ ] 20.1 Create terminal-like validation output display
- [ ] 20.2 Implement WebSocket connection for streaming output
- [ ] 20.3 Add pass/fail status indicators
- [ ] 20.4 Create "Validate Draft" button
- [ ] 20.5 Implement auto-scroll and search in console

## 21. Testing

- [ ] 21.1 Write unit tests for OpenSpecClient
- [ ] 21.2 Write unit tests for LLM providers
- [ ] 21.3 Write unit tests for path validation
- [ ] 21.4 Write unit tests for ContentVersioningService
- [ ] 21.5 Write integration tests for auth flow
- [ ] 21.6 Write integration tests for proposal lifecycle (DRAFT→REVIEW→READY)
- [ ] 21.7 Write integration tests for "Validate Draft" flow
- [ ] 21.8 Write integration tests for "Mark Ready" filesystem write
- [ ] 21.9 Write E2E tests for critical user journeys
- [ ] 21.10 Set up CI pipeline with test coverage

## 22. Documentation & Deployment

- [ ] 22.1 Write API documentation (OpenAPI/Swagger)
- [ ] 22.2 Create user guide for compliance workflows
- [ ] 22.3 Document LLM provider configuration
- [ ] 22.4 Create Dockerfile for backend and frontend
- [ ] 22.5 Write deployment guide (Docker Compose, Kubernetes)
