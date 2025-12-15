# Tasks: ComplianceFlow Platform

## 1. Project Setup

- [ ] 1.1 Initialize monorepo structure (`backend/`, `frontend/`)
- [ ] 1.2 Set up Python backend with FastAPI, SQLModel, uvicorn
- [ ] 1.3 Set up React frontend with Vite, TailwindCSS, React Flow
- [ ] 1.4 Configure ESLint, Prettier, Ruff for code quality
- [ ] 1.5 Create Docker Compose for local development
- [ ] 1.6 Set up environment configuration (.env.example)

## 2. Database Layer

- [ ] 2.1 Define SQLModel schemas: User, Project, ChangeProposal, ReviewComment, AuditLog
- [ ] 2.2 Implement optimistic locking (version field) on Project model
- [ ] 2.3 Set up Alembic migrations
- [ ] 2.4 Create database initialization script
- [ ] 2.5 Add SQLite connection with Postgres migration path

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
- [ ] 4.3 Implement `scaffold_change(path, proposal_name)` - runs `openspec scaffold`
- [ ] 4.4 Implement `validate_change(path, proposal_name)` - runs `openspec validate --strict`
- [ ] 4.5 Implement CLI output parsing (stdout/stderr capture)
- [ ] 4.6 Add retry logic with exponential backoff for transient failures
- [ ] 4.7 Implement async subprocess execution for streaming output

## 5. File System Security

- [ ] 5.1 Implement path validation against project allowlist
- [ ] 5.2 Create `validate_path()` utility with canonicalization
- [ ] 5.3 Sanitize CLI arguments to prevent injection
- [ ] 5.4 Implement file backup before LLM overwrites
- [ ] 5.5 Add project directory existence validation

## 6. Project Management

- [ ] 6.1 Create project CRUD endpoints (`/api/v1/projects`)
- [ ] 6.2 Implement `openspec.json` schema validation
- [ ] 6.3 Add project locking mechanism (lock/unlock endpoints)
- [ ] 6.4 Implement project ownership and permission assignment
- [ ] 6.5 Create project initialization flow (calls `openspec init`)

## 7. Proposal Lifecycle

- [ ] 7.1 Create proposal CRUD endpoints (`/api/v1/proposals`)
- [ ] 7.2 Implement status workflow: DRAFT → REVIEW → READY → MERGED
- [ ] 7.3 Create scaffold endpoint (calls `openspec scaffold`)
- [ ] 7.4 Implement proposal file read/write operations
- [ ] 7.5 Add status transition validation and audit logging
- [ ] 7.6 Implement proposal search/filter with pagination

## 8. LLM Integration

- [ ] 8.1 Define `LLMProvider` protocol interface
- [ ] 8.2 Implement OpenAI provider
- [ ] 8.3 Implement Anthropic provider
- [ ] 8.4 Implement Ollama provider (local)
- [ ] 8.5 Implement vLLM provider (local)
- [ ] 8.6 Create provider factory with configuration
- [ ] 8.7 Implement fallback chain logic
- [ ] 8.8 Add token usage tracking
- [ ] 8.9 Secure API key storage (encrypted config or env vars)

## 9. Iteration Engine

- [ ] 9.1 Create iteration endpoint (`POST /api/v1/proposals/{id}/iterate`)
- [ ] 9.2 Implement meta-prompt construction with context, draft, comments
- [ ] 9.3 Add file backup before overwrite
- [ ] 9.4 Implement LLM content generation call
- [ ] 9.5 Write generated content to proposal files
- [ ] 9.6 Auto-trigger validation after iteration
- [ ] 9.7 Return validation results in response

## 10. Validation Engine

- [ ] 10.1 Create validation endpoint (`POST /api/v1/proposals/{id}/validate`)
- [ ] 10.2 Parse validation output into structured result
- [ ] 10.3 Categorize errors, warnings, and passed checks
- [ ] 10.4 Store validation history for audit trail

## 11. Review System

- [ ] 11.1 Create review comment CRUD endpoints (`/api/v1/reviews`)
- [ ] 11.2 Implement comment threading on files/lines
- [ ] 11.3 Add comment selection for iteration context
- [ ] 11.4 Implement comment status workflow (open, resolved)
- [ ] 11.5 Add reviewer assignment to proposals

## 12. Real-time Updates

- [ ] 12.1 Set up WebSocket endpoint (`/ws/projects/{id}/validate`)
- [ ] 12.2 Stream CLI output in real-time during validation
- [ ] 12.3 Implement SSE fallback endpoint
- [ ] 12.4 Add WebSocket connection management (ping/pong, reconnect)
- [ ] 12.5 Create LLM streaming endpoint (`/ws/proposals/{id}/iterate`)

## 13. Audit System

- [ ] 13.1 Create AuditLog model with immutable records
- [ ] 13.2 Implement audit logging service
- [ ] 13.3 Log all state transitions and file modifications
- [ ] 13.4 Add audit log query endpoint with filters
- [ ] 13.5 Implement audit export (CSV, JSON)
- [ ] 13.6 Configure retention policy settings

## 14. Frontend - Core

- [ ] 14.1 Set up React Router with protected routes
- [ ] 14.2 Implement auth context and token management
- [ ] 14.3 Create API client with interceptors (auth, error handling)
- [ ] 14.4 Build login/logout pages
- [ ] 14.5 Create main layout with navigation

## 15. Frontend - Project Management

- [ ] 15.1 Build project list dashboard
- [ ] 15.2 Create project wizard (name, standard, directory path)
- [ ] 15.3 Implement project settings page
- [ ] 15.4 Add project lock indicator

## 16. Frontend - Proposal Management

- [ ] 16.1 Build proposal list view with pagination and filters
- [ ] 16.2 Create proposal creation form
- [ ] 16.3 Build proposal detail view with status badge
- [ ] 16.4 Implement status transition controls
- [ ] 16.5 Add proposal file browser (tree view)

## 17. Frontend - Editor & Review

- [ ] 17.1 Build markdown editor for proposal files
- [ ] 17.2 Implement diff view for LLM iterations
- [ ] 17.3 Create comment sidebar with threading
- [ ] 17.4 Add comment selection checkboxes for iteration
- [ ] 17.5 Build iteration trigger button with instruction input

## 18. Frontend - Validation Console

- [ ] 18.1 Create terminal-like validation output display
- [ ] 18.2 Implement WebSocket connection for streaming output
- [ ] 18.3 Add pass/fail status indicators
- [ ] 18.4 Create validation history panel
- [ ] 18.5 Implement auto-scroll and search in console

## 19. Testing

- [ ] 19.1 Write unit tests for OpenSpecClient
- [ ] 19.2 Write unit tests for LLM providers
- [ ] 19.3 Write unit tests for path validation
- [ ] 19.4 Write integration tests for auth flow
- [ ] 19.5 Write integration tests for proposal lifecycle
- [ ] 19.6 Write E2E tests for critical user journeys
- [ ] 19.7 Set up CI pipeline with test coverage

## 20. Documentation & Deployment

- [ ] 20.1 Write API documentation (OpenAPI/Swagger)
- [ ] 20.2 Create user guide for compliance workflows
- [ ] 20.3 Document LLM provider configuration
- [ ] 20.4 Create Dockerfile for backend and frontend
- [ ] 20.5 Write deployment guide (Docker Compose, Kubernetes)
