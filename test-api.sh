#!/bin/bash

# ThinkSync - API Endpoint Tester
# Tests all major API endpoints to verify system is working

API_URL="${1:-http://localhost:8000}"
TIMEOUT=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}ThinkSync - API Testing${NC}"
echo -e "${BLUE}API URL: $API_URL${NC}"
echo -e "${BLUE}================================================${NC}\n"

test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4

    echo -n "Testing: $description ... "
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" \
            -H "Content-Type: application/json" \
            --max-time $TIMEOUT)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" \
            --max-time $TIMEOUT)
    fi
    
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓ OK (HTTP $http_code)${NC}"
        return 0
    elif [ "$http_code" -ge 300 ] && [ "$http_code" -lt 400 ]; then
        echo -e "${YELLOW}⚠ Redirect (HTTP $http_code)${NC}"
        return 1
    elif [ "$http_code" == "401" ] || [ "$http_code" == "401" ]; then
        echo -e "${YELLOW}⚠ Unauthorized (HTTP $http_code) - Expected without login${NC}"
        return 0
    elif [ "$http_code" == "500" ]; then
        echo -e "${RED}✗ Server Error (HTTP $http_code)${NC}"
        echo -e "${RED}  Response: $body${NC}"
        return 1
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        return 1
    fi
}

# 1. Health Check
echo -e "${BLUE}1. Health Check${NC}"
test_endpoint "GET" "/health" "Health endpoint"

if [ $? -eq 0 ]; then
    # 2. Authentication
    echo -e "\n${BLUE}2. Authentication${NC}"
    test_endpoint "GET" "/auth/session" "Get session (should be 401 without auth)"
    
    # 3. Servers
    echo -e "\n${BLUE}3. Servers${NC}"
    test_endpoint "GET" "/servers" "List servers"
    
    # 4. Chats
    echo -e "\n${BLUE}4. Chats${NC}"
    test_endpoint "GET" "/chats" "List chats"
    
    # 5. Deployments
    echo -e "\n${BLUE}5. Deployments${NC}"
    test_endpoint "GET" "/deployments" "List deployments"
    
    # 6. Tasks
    echo -e "\n${BLUE}6. Tasks${NC}"
    test_endpoint "GET" "/tasks" "List tasks"
    
    # 7. Databases
    echo -e "\n${BLUE}7. Databases${NC}"
    test_endpoint "GET" "/database" "List databases"
    
    # 8. Agents
    echo -e "\n${BLUE}8. Agents${NC}"
    test_endpoint "GET" "/agents/status/test-id" "Get task status"
    
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${GREEN}✓ API Testing Complete!${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo -e "\n${YELLOW}Notes:${NC}"
    echo "• Endpoints returning 401 (Unauthorized) are expected without authentication"
    echo "• Login first to test authenticated endpoints"
    echo "• Use API documentation at $API_URL/docs"
else
    echo -e "\n${RED}✗ Health check failed - API is not responding${NC}"
    echo -e "${YELLOW}Make sure the API is running:${NC}"
    echo "  docker-compose up backend"
    exit 1
fi
