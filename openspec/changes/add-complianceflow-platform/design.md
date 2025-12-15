# Design: ComplianceFlow Platform

## Context

ComplianceFlow wraps the OpenSpec CLI with a web-based GUI for safety-critical software compliance management. The system must handle sensitive compliance documents, integrate with external LLM providers, and execute CLI commands on the host filesystem.

**Stakeholders**: Compliance officers, software architects, QA teams, auditors

**Constraints**:
- Must work with existing OpenSpec CLI (no modifications)
- Must support air-gapped deployments (local LLM option)
- Audit trail requirements for regulatory compliance
- Multi-user concurrent access

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
- Real-time collaborative editing (v1)
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

### D5: Concurrent Access - Optimistic Locking + Project Locks

**Decision**:
- Database-level optimistic locking (version field)
- Advisory project locks for CLI operations

```python
class Project(SQLModel):
    id: int
    version: int  # Incremented on each update
    locked_by: int | None
    locked_at: datetime | None
```

**Rationale**:
- Optimistic locking handles most concurrent edits
- Explicit locks prevent conflicting CLI operations

### D6: Audit Trail - Append-Only Event Log

**Decision**: Separate `AuditLog` table with immutable records

```python
class AuditLog(SQLModel):
    id: int
    timestamp: datetime
    user_id: int
    action: str  # PROPOSAL_CREATED, STATUS_CHANGED, FILE_MODIFIED, etc.
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
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   SQLite/PG   │ │  Filesystem   │ │  LLM APIs     │
│   Database    │ │  (Projects)   │ │  Cloud/Local  │
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
│ created_at   │     │ compliance_std   │     │ draft_path      │
│ last_login   │     │ locked_by (FK)   │     │ created_by (FK) │
└──────────────┘     │ locked_at        │     │ approved_by(FK) │
                     │ version          │     │ created_at      │
                     └──────────────────┘     │ updated_at      │
                                              └─────────────────┘
                                                      │
                     ┌────────────────────────────────┘
                     ▼
┌──────────────────────┐     ┌──────────────────────┐
│   ReviewComment      │     │     AuditLog         │
├──────────────────────┤     ├──────────────────────┤
│ id                   │     │ id                   │
│ proposal_id (FK)     │     │ timestamp            │
│ user_id (FK)         │     │ user_id (FK)         │
│ target_file          │     │ action               │
│ line_number          │     │ resource_type        │
│ comment_text         │     │ resource_id          │
│ status               │     │ old_value (JSON)     │
│ selected_for_iter    │     │ new_value (JSON)     │
│ created_at           │     │ ip_address           │
└──────────────────────┘     └──────────────────────┘
```

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenSpec CLI version incompatibility | High | Pin version, integration tests, version detection |
| LLM hallucination in compliance docs | High | Human review required, diff view, validation gate |
| Filesystem corruption from concurrent CLI | Medium | Project locking, atomic writes, backup before modify |
| WebSocket connection drops | Medium | Auto-reconnect, SSE fallback, operation idempotency |
| SQLite scaling limits | Low | Postgres migration path, connection pooling |
| Local LLM quality variance | Medium | Model recommendations, quality thresholds |

## Migration Plan

### Phase 1: Core Platform
1. Set up project structure (frontend/backend)
2. Implement auth system
3. Basic project management
4. OpenSpec CLI wrapper

### Phase 2: Proposal Workflow
1. Scaffold and validation integration
2. LLM integration with OpenAI/Anthropic
3. Review commenting system
4. Status workflow

### Phase 3: Production Hardening
1. WebSocket streaming
2. Local LLM support (Ollama, vLLM)
3. Comprehensive audit logging
4. Performance optimization

### Rollback
- Database migrations are versioned (Alembic)
- Feature flags for new capabilities
- Backup filesystem before destructive operations
