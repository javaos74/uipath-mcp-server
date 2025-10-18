#!/bin/bash

# Start server in background
source .venv/bin/activate
cd backend
python -m src.main > ../server.log 2>&1 &
SERVER_PID=$!
cd ..

echo "Server started with PID: $SERVER_PID"
sleep 3

# Register and login
echo "1. Registering user..."
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "role": "user"
  }' | jq '.'

echo -e "\n2. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
echo "Token: ${TOKEN:0:30}..."

# Get current user info
echo -e "\n3. Getting current user info (before UiPath config)..."
curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Update UiPath config
echo -e "\n4. Updating UiPath configuration..."
curl -s -X PUT http://localhost:8000/auth/uipath-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "uipath_url": "https://cloud.uipath.com/myaccount/mytenant",
    "uipath_access_token": "my-secret-pat-token-12345",
    "uipath_folder_path": "/Production/Finance"
  }' | jq '.'

# Get user info again
echo -e "\n5. Getting current user info (after UiPath config)..."
curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Kill server
echo -e "\n6. Stopping server..."
kill $SERVER_PID

echo "Done!"
