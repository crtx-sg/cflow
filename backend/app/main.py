"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.database import init_db
from app.routers import auth, projects, proposals, reviews, health, websocket, audit

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events."""
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Compliance management platform wrapping OpenSpec CLI",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix=settings.api_v1_prefix, tags=["auth"])
app.include_router(projects.router, prefix=settings.api_v1_prefix, tags=["projects"])
app.include_router(proposals.router, prefix=settings.api_v1_prefix, tags=["proposals"])
app.include_router(reviews.router, prefix=settings.api_v1_prefix, tags=["reviews"])
app.include_router(websocket.router, prefix=settings.api_v1_prefix, tags=["websocket"])
app.include_router(audit.router, prefix=settings.api_v1_prefix, tags=["audit"])
