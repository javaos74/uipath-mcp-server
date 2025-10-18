#!/bin/bash

# Test MCP Connection Script
# This script helps you test the MCP endpoint connection

echo "==================================="
echo "MCP Connection Test"
echo "==================================="
echo ""

# Configuration
SERVER_URL="http://localhost:8000"
TENANT_NAME="UiPath"
SERVER_NAME="CharlesTest"

# Step 1: Get access token
echo "Step 1: Getting access token..."
echo "Please enter your username:"
read USERNAME

echo "Please enter your password:"
read -s PASSWORD

echo ""
echo "Logging in..."

# Login and get token
LOGIN_RESPONSE=$(curl -s -X POST "$SERVER_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

# Extract token
TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed!"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful!"
echo "Token: ${TOKEN:0:20}..."
echo ""

# Step 2: Test MCP endpoint with Authorization header
echo "Step 2: Testing MCP endpoint with Authorization header..."
echo "URL: $SERVER_URL/mcp/$TENANT_NAME/$SERVER_NAME"
echo ""

curl -v -N -H "Authorization: Bearer $TOKEN" \
  "$SERVER_URL/mcp/$TENANT_NAME/$SERVER_NAME" 2>&1 | head -20

echo ""
echo ""

# Step 3: Test MCP endpoint with query parameter
echo "Step 3: Testing MCP endpoint with query parameter..."
echo "URL: $SERVER_URL/mcp/$TENANT_NAME/$SERVER_NAME?token=..."
echo ""

curl -v -N "$SERVER_URL/mcp/$TENANT_NAME/$SERVER_NAME?token=$TOKEN" 2>&1 | head -20

echo ""
echo ""
echo "==================================="
echo "Test completed!"
echo "==================================="
echo ""
echo "If you see '403 Forbidden', check:"
echo "  1. The server exists in the database"
echo "  2. You own the server (or are an admin)"
echo "  3. The token is valid"
echo ""
echo "If you see '200 OK' or SSE stream, the connection works!"
echo ""
echo "To use in MCP clients, use one of these formats:"
echo ""
echo "1. With Authorization header:"
echo "   URL: $SERVER_URL/mcp/$TENANT_NAME/$SERVER_NAME"
echo "   Header: Authorization: Bearer $TOKEN"
echo ""
echo "2. With query parameter:"
echo "   URL: $SERVER_URL/mcp/$TENANT_NAME/$SERVER_NAME?token=$TOKEN"
