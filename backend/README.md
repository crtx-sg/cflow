# ComplianceFlow Backend

FastAPI backend for the ComplianceFlow compliance management platform.

## Features

- JWT authentication with refresh token rotation
- Role-based access control (Admin, Reviewer, Author, Viewer)
- OpenSpec CLI integration for validation
- LLM-powered content iteration (OpenAI, Anthropic, Ollama, vLLM)
- Real-time WebSocket updates
- Comprehensive audit logging

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env

# Run server
uvicorn app.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
pytest
pytest --cov=app
```
