# ComplianceFlow Platform - Setup & Testing Guide

## Prerequisites

### Required Software
- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend runtime
- **OpenSpec CLI** - Must be installed and available in PATH
- **Git** - Version control

### Optional
- **Docker & Docker Compose** - For containerized deployment
- **PostgreSQL** - Production database (SQLite used by default)
- **Ollama** - For local LLM inference

## Quick Start

### 1. Clone and Setup

```bash
cd /home/sganesh/crtx/repo/cflow

# Create Python virtual environment
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
```

**Required environment variables:**

```env
# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=your-super-secret-key-change-me

# Database
DATABASE_URL=sqlite+aiosqlite:///./complianceflow.db

# LLM Configuration (choose one)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key

# Or for Anthropic:
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-your-api-key

# Or for local Ollama:
# LLM_PROVIDER=ollama
# LLM_BASE_URL=http://localhost:11434
# LLM_MODEL=llama3.2
```

### 3. Initialize Database

```bash
# Run migrations
alembic upgrade head

# Or create tables directly (development)
python -c "
import asyncio
from app.core.database import init_db
asyncio.run(init_db())
"
```

### 4. Create Admin User

```bash
python -c "
import asyncio
from sqlmodel import select
from app.core.database import async_session
from app.models import User, UserRole
from app.core.security import get_password_hash

async def create_admin():
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == 'admin@example.com'))
        if result.scalar_one_or_none():
            print('Admin user already exists')
            return
        admin = User(
            email='admin@example.com',
            hashed_password=get_password_hash('admin123'),
            full_name='Admin User',
            role=UserRole.ADMIN,
        )
        session.add(admin)
        await session.commit()
        print('Admin user created: admin@example.com / admin123')

asyncio.run(create_admin())
"
```

### 5. Start Backend Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Setup Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

---

## API Testing

### Using curl

#### 1. Login and Get Token

```bash
# Login
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

echo "Token: $TOKEN"
```

#### 2. Create a Project

```bash
# First, create a test directory for the project
mkdir -p /tmp/test-compliance-project

# Create project
# compliance_standard must be one of: IEC_62304, ISO_26262, DO_178C, CUSTOM
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Compliance Project",
    "local_path": "/tmp/test-compliance-project",
    "compliance_standard": "IEC_62304"
  }'
```

#### 3. List Projects

```bash
curl -X GET "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer $TOKEN"
```

#### 4. Create a Proposal

```bash
# Replace {project_id} with actual ID from previous response
curl -X POST "http://localhost:8000/api/v1/proposals/projects/1/proposals" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "add-user-authentication"
  }'
```

#### 5. Update Proposal Content

```bash
# Update proposal.md content
curl -X PUT "http://localhost:8000/api/v1/proposals/1/content/proposal.md" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# Change: Add User Authentication\n\n## Why\nWe need secure user authentication.\n\n## What Changes\n- Add login/logout endpoints\n- JWT token management\n\n## Impact\nAll API endpoints will require authentication.",
    "change_reason": "Initial draft"
  }'
```

#### 6. Validate Draft

```bash
curl -X POST "http://localhost:8000/api/v1/proposals/1/validate-draft" \
  -H "Authorization: Bearer $TOKEN"
```

#### 7. Submit for Review

```bash
curl -X POST "http://localhost:8000/api/v1/proposals/1/submit" \
  -H "Authorization: Bearer $TOKEN"
```

#### 8. Add Review Comment (as different user)

```bash
# First create a reviewer user
python -c "
import asyncio
from sqlmodel import select
from app.core.database import async_session
from app.models import User, UserRole
from app.core.security import get_password_hash

async def create_reviewer():
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == 'reviewer@example.com'))
        if result.scalar_one_or_none():
            print('Reviewer already exists')
            return
        user = User(
            email='reviewer@example.com',
            hashed_password=get_password_hash('reviewer123'),
            full_name='Reviewer User',
            role=UserRole.REVIEWER,
        )
        session.add(user)
        await session.commit()
        print('Reviewer created: reviewer@example.com / reviewer123')

asyncio.run(create_reviewer())
"

# Login as reviewer
REVIEWER_TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"reviewer@example.com","password":"reviewer123"}' | jq -r '.access_token')

# Add comment
curl -X POST "http://localhost:8000/api/v1/proposals/1/comments" \
  -H "Authorization: Bearer $REVIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "proposal.md",
    "line_start": 5,
    "content": "Please add more detail about the JWT token expiration policy."
  }'
```

#### 9. Resolve Comment (as author)

```bash
curl -X POST "http://localhost:8000/api/v1/proposals/1/comments/1/resolve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "accepted",
    "author_response": "Good point, will add JWT expiration details."
  }'
```

#### 10. Iterate with LLM

```bash
curl -X POST "http://localhost:8000/api/v1/proposals/1/iterate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "proposal.md",
    "instructions": "Add details about JWT token expiration as requested by reviewers."
  }'
```

#### 11. Mark Ready

```bash
curl -X POST "http://localhost:8000/api/v1/proposals/1/mark-ready" \
  -H "Authorization: Bearer $TOKEN"
```

#### 12. Merge (Admin only)

```bash
curl -X POST "http://localhost:8000/api/v1/proposals/1/merge" \
  -H "Authorization: Bearer $TOKEN"
```

---

## WebSocket Testing

### Using websocat

```bash
# Install websocat
cargo install websocat

# Connect to validation stream
websocat "ws://localhost:8000/api/v1/ws/proposals/1/validate?token=$TOKEN"

# Connect to iteration stream
websocat "ws://localhost:8000/api/v1/ws/proposals/1/iterate?token=$TOKEN"
# Then send: {"file_path": "proposal.md", "instructions": "Improve clarity"}
```

### Using Python

```python
import asyncio
import websockets
import json

async def test_validation_stream():
    token = "your-token-here"
    uri = f"ws://localhost:8000/api/v1/ws/proposals/1/validate?token={token}"

    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            print(f"[{data['type']}] {data.get('content', data.get('message', ''))}")
            if data['type'] in ('complete', 'error'):
                break

asyncio.run(test_validation_stream())
```

---

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test
pytest tests/test_proposals.py::test_create_proposal -v
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm run test:coverage
```

---

## Docker Deployment (Recommended)

The Docker setup provides a complete, production-ready environment with:
- **PostgreSQL 15** - Database container with health checks
- **Backend API** - FastAPI application with auto-initialization
- **Frontend** - React application

### Quick Start with Docker

```bash
cd /home/sganesh/crtx/repo/cflow

# 1. Create environment file
cp .env.example .env

# 2. Edit .env with your settings (especially LLM keys)
nano .env

# 3. Build and start all services
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. View logs
docker-compose logs -f
```

### Service URLs

Once running, access the services at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: localhost:5432

### Default Login Credentials

```
Email: admin@example.com
Password: admin123
```

### Docker Commands

```bash
# Start services in background
docker-compose up -d

# Start services with logs visible
docker-compose up

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes database!)
docker-compose down -v

# Rebuild after code changes
docker-compose up -d --build

# Check service health
docker-compose ps
```

### Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   db        │    │   backend   │    │  frontend   │     │
│  │ PostgreSQL  │◄───│   FastAPI   │◄───│    React    │     │
│  │   :5432     │    │    :8000    │    │    :5173    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│        ▲                  ▲                  ▲              │
│        │                  │                  │              │
└────────┼──────────────────┼──────────────────┼──────────────┘
         │                  │                  │
    localhost:5432    localhost:8000    localhost:5173
```

### Environment Variables

Key environment variables (set in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Database username | complianceflow |
| `POSTGRES_PASSWORD` | Database password | complianceflow |
| `SECRET_KEY` | JWT signing key | **CHANGE IN PRODUCTION** |
| `ADMIN_EMAIL` | Initial admin email | admin@example.com |
| `ADMIN_PASSWORD` | Initial admin password | admin123 |
| `LLM_PROVIDER` | LLM provider (openai/anthropic/ollama) | openai |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `PROJECTS_DIR` | Projects mount directory | ./data/projects |

### Troubleshooting Docker

#### Database connection issues
```bash
# Check if database is healthy
docker-compose ps
docker-compose logs db

# Restart database
docker-compose restart db
```

#### Backend won't start
```bash
# Check backend logs
docker-compose logs backend

# Common issues:
# - Database not ready (wait for health check)
# - Missing environment variables
# - Invalid LLM API keys
```

#### Reset everything
```bash
# Stop services and remove volumes
docker-compose down -v

# Remove built images
docker-compose down --rmi all

# Start fresh
docker-compose up -d --build
```

---

## Troubleshooting

### Common Issues

#### 1. OpenSpec CLI not found
```bash
# Verify OpenSpec is installed
which openspec
openspec --version

# If not found, install it or add to PATH
export PATH=$PATH:/path/to/openspec
```

#### 2. Database connection errors
```bash
# Check database file exists (SQLite)
ls -la backend/complianceflow.db

# Reset database
rm backend/complianceflow.db
cd backend && alembic upgrade head
```

#### 3. LLM provider errors
```bash
# Test OpenAI connection
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Ollama
curl http://localhost:11434/api/tags
```

#### 4. CORS errors in browser
- Ensure frontend origin is in `CORS_ORIGINS` in `.env`
- Default: `http://localhost:5173,http://localhost:3000`

#### 5. Token expired errors
- Access tokens expire in 15 minutes by default
- The frontend should auto-refresh using the refresh token
- Check `ACCESS_TOKEN_EXPIRE_MINUTES` in `.env`

---

## API Documentation

Once the backend is running, access the interactive API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Health Check

```bash
# Check backend health
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy"}
```

---

## Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS with proper certificates
- [ ] Configure rate limiting appropriately
- [ ] Set up log aggregation
- [ ] Configure backup for database
- [ ] Set up monitoring and alerting
- [ ] Review and restrict CORS origins
- [ ] Enable audit log retention policy
