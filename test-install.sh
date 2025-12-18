#!/bin/bash
  # test-install.sh

  echo "=== ComplianceFlow Installation Test ==="
  echo ""

  # Colors
  GREEN='\033[0;32m'
  RED='\033[0;31m'
  NC='\033[0m'

  pass() { echo -e "${GREEN}✓ $1${NC}"; }
  fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }

  # 1. Check containers
  echo "1. Checking containers..."
  docker-compose ps | grep -q "cflow-db.*Up" && pass "Database container running" || fail "Database not running"
  docker-compose ps | grep -q "cflow-backend.*Up" && pass "Backend container running" || fail "Backend not running"
  docker-compose ps | grep -q "cflow-frontend.*Up" && pass "Frontend container running" || fail "Frontend not running"

  # 2. Health check
  echo ""
  echo "2. Testing health endpoint..."
  HEALTH=$(curl -s http://localhost:8000/health)
  echo "$HEALTH" | grep -q "healthy" && pass "Backend health check passed" || fail "Backend unhealthy"

  # 3. Authentication
  echo ""
  echo "3. Testing authentication..."
  TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin@example.com&password=admin123" | jq -r '.access_token')

  [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ] && pass "Login successful" || fail "Login failed"

  # 4. API access
  echo ""
  echo "4. Testing API access..."
  USER=$(curl -s -X GET "http://localhost:8000/api/v1/auth/me" \
    -H "Authorization: Bearer $TOKEN")
  echo "$USER" | grep -q "admin@example.com" && pass "API authentication working" || fail "API auth failed"

  # 5. Frontend
  echo ""
  echo "5. Testing frontend..."
  curl -s http://localhost:5173 | grep -q "html" && pass "Frontend serving" || fail "Frontend not responding"

  echo ""
  echo "=== All tests passed! ==="
  echo ""
  echo "Access the application:"
  echo "  Frontend: http://localhost:5173"
  echo "  API Docs: http://localhost:8000/docs"
  echo "  Login:    admin@example.com / admin123"

