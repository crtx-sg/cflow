#!/bin/bash
# ComplianceFlow Quick Setup Script

set -e

echo "==================================="
echo "ComplianceFlow Setup Script"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "\n${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $(python3 --version)${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js $(node --version)${NC}"

# Check OpenSpec (optional)
if command -v openspec &> /dev/null; then
    echo -e "${GREEN}✓ OpenSpec CLI found${NC}"
else
    echo -e "${YELLOW}⚠ OpenSpec CLI not found - some features may not work${NC}"
fi

echo -e "\n${YELLOW}Step 2: Setting up backend...${NC}"
cd "$PROJECT_ROOT/backend"

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -q -e ".[dev]"
echo -e "${GREEN}✓ Backend dependencies installed${NC}"

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    # Generate a random secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/your-secret-key-change-in-production/$SECRET_KEY/" .env
    else
        sed -i "s/your-secret-key-change-in-production/$SECRET_KEY/" .env
    fi
    echo -e "${GREEN}✓ .env file created with random secret key${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Initialize database
echo "Initializing database..."
python3 -c "
import asyncio
from app.core.database import init_db
asyncio.run(init_db())
print('Database initialized')
"
echo -e "${GREEN}✓ Database initialized${NC}"

# Create admin user if not exists
echo "Creating admin user..."
python3 -c "
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
echo -e "${GREEN}✓ Admin user ready${NC}"

echo -e "\n${YELLOW}Step 3: Setting up frontend...${NC}"
cd "$PROJECT_ROOT/frontend"

# Install dependencies
echo "Installing Node.js dependencies..."
npm install --silent
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

echo -e "\n${GREEN}==================================="
echo "Setup Complete!"
echo "===================================${NC}"
echo ""
echo "To start the application:"
echo ""
echo "  Backend (terminal 1):"
echo "    cd $PROJECT_ROOT/backend"
echo "    source .venv/bin/activate"
echo "    uvicorn app.main:app --reload"
echo ""
echo "  Frontend (terminal 2):"
echo "    cd $PROJECT_ROOT/frontend"
echo "    npm run dev"
echo ""
echo "Then open: http://localhost:5173"
echo ""
echo "Login credentials:"
echo "  Email: admin@example.com"
echo "  Password: admin123"
echo ""
echo "API documentation: http://localhost:8000/docs"
