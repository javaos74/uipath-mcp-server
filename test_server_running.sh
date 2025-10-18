#!/bin/bash

# Start server in background
source .venv/bin/activate
cd backend
python -m src.main > ../server.log 2>&1 &
SERVER_PID=$!
cd ..

echo "Server started with PID: $SERVER_PID"

# Wait for server to start
sleep 3

# Test health endpoint
echo "Testing health endpoint..."
curl -s http://localhost:8000/health

# Test register
echo -e "\n\nTesting user registration..."
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "role": "user"
  }'

# Test login
echo -e "\n\nTesting login..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }')

echo "$LOGIN_RESPONSE"

# Extract token
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -n "$TOKEN" ]; then
  echo -e "\n\nToken received: ${TOKEN:0:20}..."
  
  # Test creating server
  echo -e "\n\nTesting server creation..."
  curl -s -X POST http://localhost:8000/api/servers \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
      "tenant_name": "demo",
      "server_name": "test-server",
      "description": "Test MCP server"
    }'
  
  # Test listing servers
  echo -e "\n\nTesting server list..."
  curl -s http://localhost:8000/api/servers \
    -H "Authorization: Bearer $TOKEN"
fi

# Kill server
echo -e "\n\nStopping server..."
kill $SERVER_PID

echo "Done!"
