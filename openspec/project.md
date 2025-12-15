# Project Context

## Purpose

ComplianceFlow is a production-ready compliance management platform that provides a GUI and logic wrapper around the OpenSpec CLI tool. It enables safety-critical software teams to draft, validate, iterate, and implement compliance proposals through an intuitive web interface with LLM-assisted content generation.

**Target Users**: Compliance officers, software architects, QA teams, and auditors working on IEC 62304 (medical), ISO 26262 (automotive), DO-178C (aerospace), and similar safety standards.

## Tech Stack

### Backend
- Python 3.11+
- FastAPI (async web framework)
- SQLModel (ORM with Pydantic)
- SQLite (development) / PostgreSQL (production)
- Alembic (migrations)
- uvicorn (ASGI server)

### Frontend
- React 18+ (Vite)
- TailwindCSS
- React Flow (diagram visualization)
- TypeScript

### Infrastructure
- Docker / Docker Compose
- OpenSpec CLI (`pip install openspec`)

## Project Conventions

### Code Style

**Python**:
- Follow PEP 8 with line length 100
- Use type hints for all function signatures
- Use Ruff for linting and formatting
- Async-first approach for I/O operations

**TypeScript/React**:
- Use functional components with hooks
- Prefer named exports
- Use ESLint + Prettier
- Component files: PascalCase (e.g., `ProposalEditor.tsx`)

### Architecture Patterns

- **Backend**: Service-oriented with dependency injection
  - `routers/` - API endpoints
  - `services/` - Business logic
  - `models/` - SQLModel schemas
  - `schemas/` - Pydantic request/response models

- **Frontend**: Feature-based structure
  - `features/{feature}/` - Components, hooks, and state for each feature
  - `components/` - Shared UI components
  - `hooks/` - Shared custom hooks
  - `api/` - API client and types

### Testing Strategy

- Unit tests: pytest (backend), Vitest (frontend)
- Integration tests: pytest with test database
- E2E tests: Playwright
- Minimum 80% coverage for new code

### Git Workflow

- Branch naming: `{type}/{description}` (e.g., `feat/proposal-validation`, `fix/auth-refresh`)
- Commit messages: Conventional commits (feat, fix, docs, refactor, test, chore)
- PR required for main branch
- Squash merge preferred

## Domain Context

### Compliance Standards
- **IEC 62304**: Medical device software lifecycle
- **ISO 26262**: Automotive functional safety
- **DO-178C**: Airborne software certification
- **CUSTOM**: User-defined safety rules

### Key Concepts
- **Proposal**: A change request with requirements, design, and tasks
- **Validation**: Running `openspec validate` to check traceability and completeness
- **Iteration**: LLM-assisted revision of proposal content based on review comments
- **Safety Level**: Risk classification (A, B, C for IEC 62304; ASIL A-D for ISO 26262)

### Workflow States
1. **DRAFT**: Proposal being written, can be edited
2. **REVIEW**: Submitted for review, comments allowed
3. **READY**: Approved, waiting for implementation
4. **MERGED**: Implemented and archived

## Important Constraints

### Security
- All file operations must validate paths against project root
- API keys stored encrypted or via environment variables
- Rate limiting on all endpoints
- Audit trail for all state changes

### Performance
- Pagination required for lists > 50 items
- WebSocket for streaming CLI output
- Async subprocess for CLI execution

### Compatibility
- OpenSpec CLI version must be pinned
- Support air-gapped deployments with local LLM (Ollama/vLLM)

## External Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| OpenSpec CLI | Core compliance tooling | `pip install openspec`, version pinned |
| OpenAI API | LLM completions | Optional, cloud provider |
| Anthropic API | LLM completions | Optional, cloud provider |
| Ollama | Local LLM inference | For air-gapped deployments |
| vLLM | Local LLM inference | High-performance local option |
