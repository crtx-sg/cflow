# ComplianceFlow

A production-ready compliance management platform that provides a GUI and logic wrapper around the OpenSpec CLI tool. It enables safety-critical software teams to draft, validate, iterate, and implement compliance proposals through an intuitive web interface with LLM-assisted content generation.

## Overview

ComplianceFlow helps compliance officers, software architects, QA teams, and auditors working on safety-critical standards such as:

- **IEC 62304** - Medical device software lifecycle
- **ISO 26262** - Automotive functional safety
- **DO-178C** - Airborne software certification
- **Custom standards** - User-defined safety rules

## Features

- **Project Management**: Create and manage compliance projects with configurable standards
- **Change Proposals**: Draft, review, and track compliance change proposals
- **AI-Assisted Generation**: Generate proposals from detailed system context using LLM
- **OpenSpec Integration**: Validate proposals against compliance requirements
- **Role-Based Access Control**: Admin, Reviewer, Author, and Viewer roles
- **Content Versioning**: Track all changes with full version history
- **Audit Logging**: Comprehensive audit trail for compliance evidence
- **Real-time Updates**: WebSocket support for live notifications

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Projects  │  │  Proposals  │  │  AI Wizard  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Routers   │  │  Services   │  │    Models   │              │
│  │  - auth     │  │  - audit    │  │  - user     │              │
│  │  - projects │  │  - llm      │  │  - project  │              │
│  │  - proposals│  │  - openspec │  │  - proposal │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │ OpenSpec CLI│  │   LLM Provider  │
│   (Database)    │  │ (Validation)│  │ (AI Generation) │
└─────────────────┘  └─────────────┘  └─────────────────┘
```

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Runtime |
| FastAPI | Async web framework |
| SQLModel | ORM with Pydantic integration |
| PostgreSQL | Production database |
| SQLite | Development database |
| Alembic | Database migrations |
| uvicorn | ASGI server |

### Frontend
| Technology | Purpose |
|------------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool |
| TailwindCSS | Styling |
| React Query | Data fetching |
| React Router | Navigation |
| React Flow | Diagram visualization |
| Zustand | State management |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Docker Compose | Multi-container orchestration |
| OpenSpec CLI | Compliance validation |

### LLM Providers
| Provider | Use Case |
|----------|----------|
| OpenAI | Cloud-based (GPT-4) |
| Anthropic | Cloud-based (Claude) |
| Ollama | Local/air-gapped deployments |
| vLLM | High-performance local inference |

## Project Structure

```
cflow/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, database, security
│   │   ├── models/         # SQLModel schemas
│   │   ├── routers/        # API endpoints
│   │   ├── schemas/        # Pydantic models
│   │   ├── services/       # Business logic
│   │   │   └── llm/        # LLM provider implementations
│   │   └── main.py         # FastAPI application
│   ├── alembic/            # Database migrations
│   ├── tests/              # pytest tests
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/     # Shared UI components
│   │   ├── contexts/       # React contexts
│   │   ├── pages/          # Page components
│   │   ├── services/       # API client
│   │   └── App.tsx
│   ├── Dockerfile
│   └── package.json
├── data/
│   └── projects/           # Mounted project directories
├── openspec/               # OpenSpec change proposals
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 1. Clone the Repository

```bash
git clone <repository-url>
cd cflow
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` to configure:

```bash
# Database
POSTGRES_USER=complianceflow
POSTGRES_PASSWORD=complianceflow
POSTGRES_DB=complianceflow

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=your-secure-secret-key

# Admin user
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123

# LLM Provider (choose one)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-your-api-key

# Or use Ollama for local LLM
# LLM_PROVIDER=ollama
# LLM_BASE_URL=http://host.docker.internal:11434
# LLM_MODEL=llama3.2
```

### 3. Start Services

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** on port 5432
- **Backend API** on port 8000
- **Frontend** on port 5173

### 4. Access the Application

- **Frontend**: http://localhost:5173
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

Login with the admin credentials configured in `.env`.

## Docker Setup

### Services

| Service | Port | Description |
|---------|------|-------------|
| `db` | 5432 | PostgreSQL 15 database |
| `backend` | 8000 | FastAPI backend |
| `frontend` | 5173 | React frontend (Vite dev server) |

### Volumes

- `postgres_data` - Persistent database storage
- `${PROJECTS_DIR}:/projects` - Mount for OpenSpec project directories

### Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

### Using Local LLM (Ollama)

For air-gapped deployments or to avoid cloud API costs:

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama3.2`
3. Configure in `.env`:
   ```bash
   LLM_PROVIDER=ollama
   LLM_BASE_URL=http://host.docker.internal:11434
   LLM_MODEL=llama3.2
   ```
4. Ensure Ollama is listening on all interfaces:
   ```bash
   OLLAMA_HOST=0.0.0.0 ollama serve
   ```

## Development Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/unit/test_security.py

# Run with verbose output
pytest -v
```

### Test Structure

```
backend/tests/
├── conftest.py          # Fixtures and configuration
├── unit/                # Unit tests
│   ├── test_security.py
│   └── test_filesystem.py
└── integration/         # Integration tests
    └── test_auth.py
```

### Test Database

Tests use an in-memory SQLite database configured in `conftest.py`. Each test function gets a fresh database instance.

### Available Fixtures

| Fixture | Description |
|---------|-------------|
| `client` | Async HTTP test client |
| `test_session` | Database session |
| `admin_user` | Admin user instance |
| `author_user` | Author user instance |
| `reviewer_user` | Reviewer user instance |
| `admin_token` | JWT token for admin |
| `author_token` | JWT token for author |
| `reviewer_token` | JWT token for reviewer |

### Example Test

```python
import pytest
from tests.conftest import auth_headers

@pytest.mark.asyncio
async def test_create_project(client, admin_token):
    response = await client.post(
        "/api/v1/projects",
        json={"name": "test-project", "local_path": "/projects/test"},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 201
    assert response.json()["name"] == "test-project"
```

### Frontend Tests

```bash
cd frontend

# Run tests (when configured)
npm run test

# Run linter
npm run lint
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login with email/password |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Logout and invalidate refresh token |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/projects` | List projects |
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects/{id}` | Get project details |
| PUT | `/api/v1/projects/{id}` | Update project |
| DELETE | `/api/v1/projects/{id}` | Delete project |
| POST | `/api/v1/projects/{id}/analyze-proposals` | AI-analyze context |
| POST | `/api/v1/projects/{id}/create-proposals` | Batch create proposals |

### Proposals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/proposals/projects/{id}/proposals` | List project proposals |
| POST | `/api/v1/proposals/projects/{id}/proposals` | Create proposal |
| GET | `/api/v1/proposals/{id}` | Get proposal details |
| POST | `/api/v1/proposals/{id}/submit` | Submit for review |
| POST | `/api/v1/proposals/{id}/validate-draft` | Validate proposal |
| GET | `/api/v1/proposals/{id}/content/{path}` | Get file content |
| PUT | `/api/v1/proposals/{id}/content/{path}` | Update file content |

## Workflow States

```
DRAFT ──────► REVIEW ──────► READY ──────► MERGED
  │             │              │
  │             │              │
  ▼             ▼              ▼
 Edit       Comments       Implement
 content    & feedback     changes
```

1. **DRAFT**: Proposal is being written, can be freely edited
2. **REVIEW**: Submitted for review, comments can be added
3. **READY**: Approved by reviewers, waiting for implementation
4. **MERGED**: Implemented and archived

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | complianceflow | Database user |
| `POSTGRES_PASSWORD` | complianceflow | Database password |
| `POSTGRES_DB` | complianceflow | Database name |
| `SECRET_KEY` | (required) | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 15 | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token TTL |
| `ADMIN_EMAIL` | admin@example.com | Initial admin email |
| `ADMIN_PASSWORD` | admin123 | Initial admin password |
| `LLM_PROVIDER` | openai | LLM provider (openai/anthropic/ollama/vllm) |
| `LLM_MODEL` | gpt-4 | Model name |
| `LLM_BASE_URL` | - | Custom API base URL |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `OPENSPEC_TIMEOUT` | 60 | CLI command timeout (seconds) |
| `PROJECTS_DIR` | ./data/projects | Projects mount directory |
| `DEBUG` | false | Enable debug mode |

## Security Considerations

- Change `SECRET_KEY` in production
- Use strong passwords for admin and database
- Store API keys securely (environment variables or secrets manager)
- Enable HTTPS in production (reverse proxy recommended)
- Review CORS settings for your deployment
- Regular security updates for dependencies

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
