#!/bin/bash

# ThinkSync - Deployment Validation Script
# This script verifies all components are properly configured and connected

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}ThinkSync - Deployment Validation${NC}"
echo -e "${BLUE}================================================${NC}\n"

# Check function
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
        exit 1
    fi
}

warn_status() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 1. Check if .env file exists
echo -e "${BLUE}1. Environment Configuration${NC}"
if [ -f .env.local ]; then
    echo -e "${GREEN}✓ .env.local found${NC}"
else
    cp .env.example .env.local 2>/dev/null || true
    warn_status ".env.local not found - using defaults"
fi

# 2. Check Docker and Docker Compose
echo -e "\n${BLUE}2. Docker Setup${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    warn_status "Docker not found - required for deployment"
fi

if command -v docker-compose &> /dev/null || command -v docker compose &> /dev/null; then
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    warn_status "Docker Compose not found"
fi

# 3. Check Python
echo -e "\n${BLUE}3. Python Setup${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION installed${NC}"
else
    warn_status "Python 3 not found"
fi

# 4. Check Node.js
echo -e "\n${BLUE}4. Node.js Setup${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION installed${NC}"
else
    warn_status "Node.js not found"
fi

# 5. Check Redis (if running)
echo -e "\n${BLUE}5. Redis Configuration${NC}"
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis is running${NC}"
    else
        warn_status "Redis CLI found but not running"
    fi
else
    warn_status "Redis CLI not found - will use Docker container"
fi

# 6. Check required files
echo -e "\n${BLUE}6. Project Files${NC}"
files=(
    "backend/main.py"
    "backend/config.py"
    "backend/requirements.txt"
    "frontend/package.json"
    "docker-compose.yml"
    "Dockerfile"
    "frontend/Dockerfile"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file${NC}"
    else
        echo -e "${RED}✗ $file missing${NC}"
    fi
done

# 7. Check Python dependencies (if venv exists)
echo -e "\n${BLUE}7. Backend Dependencies${NC}"
if [ -d "backend/.venv" ] || [ -d "venv" ]; then
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
    
    # Try to check if required packages are installed
    if python3 -c "import fastapi, supabase, redis" 2>/dev/null; then
        echo -e "${GREEN}✓ Required Python packages installed${NC}"
    else
        warn_status "Some Python packages may not be installed"
    fi
else
    warn_status "Virtual environment not created - run: cd backend && python3 -m venv .venv"
fi

# 8. Check Node dependencies
echo -e "\n${BLUE}8. Frontend Dependencies${NC}"
if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}✓ Node modules installed${NC}"
else
    warn_status "Node modules not installed - run: cd frontend && npm install"
fi

# 9. Test environment variables
echo -e "\n${BLUE}9. Environment Variables${NC}"
if grep -q "SUPABASE_URL" .env.local 2>/dev/null; then
    SUPABASE_URL=$(grep SUPABASE_URL .env.local | cut -d '=' -f 2)
    if [ ! -z "$SUPABASE_URL" ] && [ "$SUPABASE_URL" != "" ]; then
        echo -e "${GREEN}✓ SUPABASE_URL configured${NC}"
    else
        warn_status "SUPABASE_URL is empty"
    fi
fi

if grep -q "OPENAI_API_KEY" .env.local 2>/dev/null; then
    OPENAI_KEY=$(grep OPENAI_API_KEY .env.local | cut -d '=' -f 2)
    if [ ! -z "$OPENAI_KEY" ] && [ "$OPENAI_KEY" != "" ]; then
        echo -e "${GREEN}✓ OPENAI_API_KEY configured${NC}"
    else
        warn_status "OPENAI_API_KEY is empty"
    fi
fi

# 10. Port availability check
echo -e "\n${BLUE}10. Port Availability${NC}"
if netstat -tuln 2>/dev/null | grep -q ":8000 "; then
    warn_status "Port 8000 is already in use"
else
    echo -e "${GREEN}✓ Port 8000 available${NC}"
fi

if netstat -tuln 2>/dev/null | grep -q ":3000 "; then
    warn_status "Port 3000 is already in use"
else
    echo -e "${GREEN}✓ Port 3000 available${NC}"
fi

# 11. Git status
echo -e "\n${BLUE}11. Git Repository${NC}"
if [ -d ".git" ]; then
    echo -e "${GREEN}✓ Git repository initialized${NC}"
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    echo -e "${BLUE}  Current branch: $CURRENT_BRANCH${NC}"
else
    warn_status "Not a git repository"
fi

# 12. Summary
echo -e "\n${BLUE}================================================${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}================================================${NC}\n"

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Ensure all required environment variables are set in .env.local"
echo "2. Test with: docker-compose up --build"
echo "3. Check health: curl http://localhost:8000/health"
echo "4. Access frontend: http://localhost:3000"
echo "5. View API docs: http://localhost:8000/docs"
echo ""

echo -e "${YELLOW}For Production Deployment:${NC}"
echo "1. Follow instructions in DEPLOYMENT.md"
echo "2. Use .env.production as template"
echo "3. Configure SSL certificates"
echo "4. Set up database backups"
echo "5. Configure monitoring and logging"
echo ""

echo -e "${GREEN}✓ Validation Complete!${NC}"
