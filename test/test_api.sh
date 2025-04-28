#!/bin/bash
# test_api.sh - Test script to verify the Flask API endpoints using curl

# Text colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Server details
API_HOST="localhost"
API_PORT="5000"
BASE_URL="http://${API_HOST}:${API_PORT}"

# Print header
echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}    Flask API Server Test Script     ${NC}"
echo -e "${BLUE}=======================================${NC}"
echo

# Function to test an endpoint with curl
test_endpoint() {
    local endpoint=$1
    local method=$2
    local data=$3
    local description=$4
    
    echo -e "${YELLOW}Testing: ${description} (${method} ${endpoint})${NC}"
    
    if [ "$method" == "GET" ]; then
        # For GET requests
        response=$(curl -s -X GET "${BASE_URL}${endpoint}")
    else
        # For POST requests with JSON data
        response=$(curl -s -X POST "${BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "${data}")
    fi
    
    # Check if response is valid JSON
    if echo "$response" | jq . >/dev/null 2>&1; then
        # Format and print the JSON response
        echo -e "${GREEN}Response:${NC}"
        echo "$response" | jq .
        echo -e "${GREEN}✓ Success${NC}"
    else
        # Print the raw response if not valid JSON
        echo -e "${RED}Error: Couldn't parse response as JSON${NC}"
        echo -e "${RED}Raw response: $response${NC}"
        echo -e "${RED}✗ Failed${NC}"
    fi
    echo -e "${BLUE}---------------------------------------${NC}"
    echo
}

# Check if API server is running
if ! curl -s "${BASE_URL}" > /dev/null; then
    echo -e "${RED}Error: API server is not running at ${BASE_URL}${NC}"
    echo -e "${YELLOW}Please start the server first:${NC}"
    echo -e "python app.py"
    exit 1
fi

echo -e "${GREEN}API server is running at ${BASE_URL}${NC}"
echo

# Test base endpoint
test_endpoint "/" "GET" "" "Base Endpoint"

# Test system stats endpoint
test_endpoint "/api/system" "GET" "" "System Statistics"

# Test Docker containers endpoint
test_endpoint "/api/docker" "GET" "" "Docker Containers"

# Test command execution endpoint with a simple command
command_data='{"command": "echo Hello from the API test script!"}'
test_endpoint "/api/execute" "POST" "$command_data" "Command Execution"

# Test scripts list endpoint
test_endpoint "/api/scripts" "GET" "" "List Available Scripts"

# Test synchronous script execution (system-status)
test_endpoint "/api/scripts/system-status" "POST" "{}" "Execute System Status Script"

# Test asynchronous script execution (long-task)
long_task_data='{"task_name": "test-task", "duration": 10}'
test_endpoint "/api/scripts/long-task" "POST" "$long_task_data" "Execute Long Task Script"

# Summary
echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}API Test Script Completed${NC}"
echo -e "${BLUE}=======================================${NC}"
echo
echo -e "${YELLOW}If all tests show 'Success', your API server is working correctly.${NC}"
echo