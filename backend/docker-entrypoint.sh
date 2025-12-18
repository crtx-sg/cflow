#!/bin/bash
set -e

echo "==================================="
echo "ComplianceFlow Backend Starting..."
echo "==================================="

# Wait for database to be ready
if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    echo "Waiting for PostgreSQL to be ready..."

    # Extract host and port from DATABASE_URL
    # Format: postgresql+asyncpg://user:pass@host:port/db
    DB_HOST=$(echo $DATABASE_URL | sed -E 's/.*@([^:]+):.*/\1/')
    DB_PORT=$(echo $DATABASE_URL | sed -E 's/.*:([0-9]+)\/.*/\1/')

    # Default port if not found
    if [ -z "$DB_PORT" ] || [ "$DB_PORT" == "$DATABASE_URL" ]; then
        DB_PORT=5432
    fi

    # Wait for PostgreSQL
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do
        echo "PostgreSQL is unavailable at $DB_HOST:$DB_PORT - sleeping..."
        sleep 2
    done

    echo "PostgreSQL is ready!"
fi

# Initialize database
echo "Initializing database..."
python -c "
import asyncio
# Import all models first so SQLModel.metadata knows about them
from app.models import User, Project, ChangeProposal, ProposalContent, ContentVersion, ReviewComment, AuditLog, LLMUsage
from app.core.database import init_db
asyncio.run(init_db())
print('Database tables created.')
"

# Create admin user if ADMIN_EMAIL and ADMIN_PASSWORD are set
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "Creating admin user..."
    python -c "
import asyncio
from sqlmodel import select
from app.core.database import async_session
from app.models import User, UserRole
from app.core.security import get_password_hash
import os

async def create_admin():
    email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    full_name = os.environ.get('ADMIN_FULLNAME', 'Admin User')

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print(f'Admin user {email} already exists')
            return

        admin = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserRole.ADMIN,
        )
        session.add(admin)
        await session.commit()
        print(f'Admin user created: {email}')

asyncio.run(create_admin())
"
fi

echo "==================================="
echo "Starting application server..."
echo "==================================="

# Execute the main command
exec "$@"
