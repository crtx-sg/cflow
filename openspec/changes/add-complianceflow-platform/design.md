# Design: ComplianceFlow Platform

## Context

ComplianceFlow wraps the OpenSpec CLI with a web-based GUI for safety-critical software compliance management. The system must handle sensitive compliance documents, integrate with external LLM providers, and execute CLI commands on the host filesystem.

**Stakeholders**: Compliance officers, software architects, QA teams, auditors

**Constraints**:
- Must work with existing OpenSpec CLI (no modifications)
- Must support air-gapped deployments (local LLM option)
- Audit trail requirements for regulatory compliance
- Single Author editing model (no concurrent edits)

## Goals / Non-Goals

### Goals
- Provide intuitive GUI for OpenSpec workflow
- Enable LLM-assisted content generation with human oversight
- Ensure security for filesystem and CLI operations
- Support real-time feedback during validation
- Maintain comprehensive audit trail
- Scale from single-user to team deployments

### Non-Goals
- Replacing OpenSpec CLI functionality
- Building a general-purpose document editor
- Real-time collaborative editing (single Author model)
- Mobile-first design (v1)

## Decisions

### D1: Authentication - JWT with Refresh Tokens

**Decision**: Use JWT access tokens (15min) with HTTP-only refresh tokens (7d)

**Rationale**:
- Stateless authentication scales horizontally
- Refresh token rotation prevents token theft
- HTTP-only cookies prevent XSS token extraction

**Alternatives Considered**:
- Session-based: Requires server-side session store, complicates scaling
- OAuth2 only: Overkill for initial deployment, can add later

### D2: LLM Integration - Provider-Agnostic Abstraction

**Decision**: Abstract LLM calls behind `LLMProvider` interface with pluggable backends

```python
class LLMProvider(Protocol):
    async def complete(self, prompt: str, config: LLMConfig) -> LLMResponse: ...
    async def stream(self, prompt: str, config: LLMConfig) -> AsyncIterator[str]: ...
```

**Supported Providers**:
- OpenAI API
- Anthropic API
- Local: Ollama, vLLM (for air-gapped deployments)

**Rationale**:
- Supports cloud and local models without code changes
- Enables fallback chains (primary → secondary → local)
- Simplifies testing with mock provider

**Alternatives Considered**:
- Direct OpenAI SDK: Vendor lock-in, no fallback
- LangChain: Heavy dependency, abstraction overkill for our use case

### D3: File System Security - Sandboxed Execution

**Decision**:
1. Validate all paths against project-specific allowlist
2. Execute CLI in subprocess with restricted environment
3. Use `pathlib` for path canonicalization (prevents traversal)

```python
def validate_path(path: Path, project: Project) -> Path:
    canonical = path.resolve()
    allowed_root = Path(project.local_path).resolve()
    if not canonical.is_relative_to(allowed_root):
        raise SecurityError(f"Path {path} outside project root")
    return canonical
```

**Rationale**:
- Defense in depth: validation + sandboxing
- Audit-friendly with explicit allowlist
- Only applies when writing to filesystem (READY state)

### D4: Real-time Updates - WebSocket + Server-Sent Events

**Decision**:
- WebSocket for bidirectional communication (validation progress)
- SSE fallback for simpler streaming scenarios

**Rationale**:
- WebSocket provides low-latency updates for CLI output
- SSE works through proxies that block WebSocket

**Implementation**:
```python
@router.websocket("/ws/projects/{project_id}/validate")
async def validation_stream(websocket: WebSocket, project_id: int):
    process = await run_validation_async(project_id)
    async for line in process.stdout:
        await websocket.send_json({"type": "output", "data": line})
```

### D5: Database-First Content Management

**Decision**: Store proposal content in database during DRAFT and REVIEW states; write to filesystem only on READY transition.

**Rationale**:
- **No file locking needed**: Single Author edit model eliminates concurrent access conflicts
- **Atomic operations**: Database transactions easier than file operations
- **Built-in versioning**: All changes tracked automatically in database
- **Simpler conflict prevention**: Author is sole editor during DRAFT/REVIEW
- **Cleaner filesystem**: Only finalized proposals exist on disk

**Implementation**:
```python
class ProposalContent(SQLModel, table=True):
    id: int = Field(primary_key=True)
    proposal_id: int = Field(foreign_key="changeproposal.id")
    file_path: str  # e.g., "proposal.md", "specs/auth/spec.md"
    content: str  # Full file content
    version: int
    updated_by: int = Field(foreign_key="user.id")
    updated_at: datetime

class ContentVersion(SQLModel, table=True):
    id: int = Field(primary_key=True)
    proposal_id: int = Field(foreign_key="changeproposal.id")
    file_path: str
    content: str
    version: int
    created_by: int = Field(foreign_key="user.id")
    created_at: datetime
    change_reason: str | None
```

**Workflow**:
1. DRAFT/REVIEW: All edits go to `ProposalContent` table
2. Each edit creates entry in `ContentVersion` for history
3. "Validate Draft": Write to temp dir → run CLI → cleanup
4. "Mark Ready": Write all `ProposalContent` to filesystem → validate → confirm

### D6: Audit Trail - Append-Only Event Log

**Decision**: Separate `AuditLog` table with immutable records

```python
class AuditLog(SQLModel, table=True):
    id: int = Field(primary_key=True)
    timestamp: datetime
    user_id: int
    action: str  # PROPOSAL_CREATED, STATUS_CHANGED, CONTENT_MODIFIED, etc.
    resource_type: str
    resource_id: int
    old_value: str | None  # JSON
    new_value: str | None  # JSON
    ip_address: str
```

**Rationale**:
- Compliance requirement for audit trails
- JSON values enable flexible schema
- Immutable design prevents tampering

### D7: CLI Error Handling - Retry with Exponential Backoff

**Decision**: Retry transient failures (timeout, resource exhaustion) with backoff

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(CLITimeoutError)
)
async def run_openspec_command(cmd: list[str]) -> CLIResult:
    ...
```

**Rationale**:
- CLI can fail due to filesystem locks, resource contention
- Max 3 retries prevents infinite loops

### D8: API Versioning - URL Path Versioning

**Decision**: Version in URL path (`/api/v1/...`)

**Rationale**:
- Explicit, cache-friendly
- Easy to deprecate old versions

### D9: Compliance Standard - Single Standard Per Project

**Decision**: Each project has exactly one compliance standard (IEC 62304, ISO 26262, DO-178C, etc.)

**Rationale**:
- Simplifies validation rules and safety level enforcement
- Avoids conflicting requirements across standards
- Projects needing multiple standards can create separate linked projects

### D10: Large Proposal Handling - Pagination

**Decision**: Paginate file lists and validation results in UI for proposals with many files

**Implementation**:
- Default page size: 50 items
- Streaming validation output (WebSocket)
- Lazy-load file contents on demand

**Rationale**:
- Maintains UI responsiveness for 100+ file proposals
- Reduces initial load time and memory usage

### D11: Air-Gapped Deployment - Local LLM Support

**Decision**: Support Ollama and vLLM as local LLM backends

**Configuration**:
```python
class LLMConfig(BaseModel):
    provider: Literal["openai", "anthropic", "ollama", "vllm"]
    base_url: str | None  # For local providers
    model: str
    api_key: str | None  # Not required for local
```

**Rationale**:
- Enables fully air-gapped deployments
- Ollama for ease of use, vLLM for performance
- Same abstraction layer, no code changes needed

### D12: Comment Resolution Workflow

**Decision**: Comments follow status workflow: OPEN → ACCEPTED/REJECTED/DEFERRED

**Implementation**:
```python
class CommentStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"

class ReviewComment(SQLModel, table=True):
    id: int = Field(primary_key=True)
    proposal_id: int = Field(foreign_key="changeproposal.id")
    user_id: int = Field(foreign_key="user.id")
    target_file: str
    line_number: int | None
    comment_text: str
    status: CommentStatus = CommentStatus.OPEN
    author_response: str | None  # Reason for accept/reject/defer
    selected_for_iteration: bool = False
    created_at: datetime
    resolved_at: datetime | None
```

**Rationale**:
- Clear workflow for comment resolution
- Author provides reasoning for each decision
- Only ACCEPTED comments included in LLM iteration
- Transition guard: all OPEN comments must be resolved before READY

### D13: Validate Draft - Temporary Filesystem Write

**Decision**: "Validate Draft" writes content to temp directory, runs OpenSpec CLI, then cleans up

**Implementation**:
```python
async def validate_draft(proposal_id: int) -> ValidationResult:
    proposal = get_proposal(proposal_id)
    contents = get_proposal_contents(proposal_id)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Write all content files to temp structure
        for content in contents:
            file_path = Path(temp_dir) / content.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.content)

        # Run OpenSpec validation
        result = await openspec_client.validate_change(temp_dir, proposal.name)

        # Temp dir auto-cleaned up
        return result
```

**Rationale**:
- Enables validation without committing to filesystem
- Catches errors early in DRAFT/REVIEW states
- No cleanup needed (temp dir auto-deleted)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  React + Vite + TailwindCSS + React Flow                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │ Auth Pages  │ │ Dashboard   │ │ Proposal Editor     │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │ Project Wiz │ │ Review UI   │ │ Validation Console  │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                      Backend (FastAPI)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    API Layer                          │   │
│  │  /api/v1/auth  /api/v1/projects  /api/v1/proposals   │   │
│  │  /api/v1/reviews  /ws/validate  /ws/llm-stream       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │ Auth Svc    │ │ Project Svc │ │ Proposal Svc        │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │ LLM Svc     │ │ OpenSpec Cl │ │ Audit Svc           │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Content Versioning Svc                  │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   SQLite/PG   │ │  Filesystem   │ │  LLM APIs     │
│   Database    │ │ (READY only)  │ │  Cloud/Local  │
└───────────────┘ └───────────────┘ └───────────────┘
```

## Database Schema

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│    User      │     │     Project      │     │ ChangeProposal  │
├──────────────┤     ├──────────────────┤     ├─────────────────┤
│ id           │──┐  │ id               │──┐  │ id              │
│ email        │  │  │ name             │  │  │ project_id (FK) │
│ hashed_pass  │  │  │ local_path       │  │  │ name (slug)     │
│ role         │  └──│ owner_id (FK)    │  └──│ status          │
│ created_at   │     │ compliance_std   │     │ author_id (FK)  │
│ last_login   │     │ created_at       │     │ filesystem_path │
└──────────────┘     └──────────────────┘     │ created_at      │
                                              │ updated_at      │
                                              └─────────────────┘
                                                      │
        ┌─────────────────────────────────────────────┤
        ▼                                             ▼
┌──────────────────────┐     ┌──────────────────────────────┐
│   ProposalContent    │     │      ContentVersion          │
├──────────────────────┤     ├──────────────────────────────┤
│ id                   │     │ id                           │
│ proposal_id (FK)     │     │ proposal_id (FK)             │
│ file_path            │     │ file_path                    │
│ content (TEXT)       │     │ content (TEXT)               │
│ version              │     │ version                      │
│ updated_by (FK)      │     │ created_by (FK)              │
│ updated_at           │     │ created_at                   │
└──────────────────────┘     │ change_reason                │
                             └──────────────────────────────┘

┌──────────────────────┐     ┌──────────────────────┐
│   ReviewComment      │     │     AuditLog         │
├──────────────────────┤     ├──────────────────────┤
│ id                   │     │ id                   │
│ proposal_id (FK)     │     │ timestamp            │
│ user_id (FK)         │     │ user_id (FK)         │
│ target_file          │     │ action               │
│ line_number          │     │ resource_type        │
│ comment_text         │     │ resource_id          │
│ status (ENUM)        │     │ old_value (JSON)     │
│ author_response      │     │ new_value (JSON)     │
│ selected_for_iter    │     │ ip_address           │
│ created_at           │     └──────────────────────┘
│ resolved_at          │
└──────────────────────┘
```

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenSpec CLI version incompatibility | High | Pin version, integration tests, version detection |
| LLM hallucination in compliance docs | High | Human review required, diff view, validation gate |
| Large content in database | Low | TEXT columns handle 50KB+ content, index on proposal_id |
| Validation failure at READY | Medium | "Validate Draft" catches errors early |
| WebSocket connection drops | Medium | Auto-reconnect, SSE fallback, operation idempotency |
| SQLite scaling limits | Low | Postgres migration path, connection pooling |
| Local LLM quality variance | Medium | Model recommendations, quality thresholds |

## Migration Plan

### Phase 1: Core Platform
1. Set up project structure (frontend/backend)
2. Implement auth system
3. Basic project management
4. Database schema with content tables

### Phase 2: Proposal Workflow
1. Proposal CRUD with database content storage
2. Content versioning system
3. Review commenting with status workflow
4. LLM integration with OpenAI/Anthropic

### Phase 3: Validation & Filesystem
1. "Validate Draft" with temp filesystem
2. "Mark Ready" filesystem write
3. OpenSpec CLI integration
4. WebSocket streaming

### Phase 4: Production Hardening
1. Local LLM support (Ollama, vLLM)
2. Comprehensive audit logging
3. Performance optimization
4. E2E testing

### Rollback
- Database migrations are versioned (Alembic)
- Feature flags for new capabilities
- Content versions allow rollback to any state
