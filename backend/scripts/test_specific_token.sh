#!/bin/bash

# Test with the specific token from database
TOKEN="x8-hKN2oux5q4h0RruMiiSsJjQQPhoCYZZIQqJKjhgo"
TENANT="UiPath"
SERVER="CharlesTest"
URL="http://localhost:8000"

echo "=========================================="
echo "Testing MCP Access with Server API Token"
echo "=========================================="
echo ""
echo "Server: $TENANT/$SERVER"
echo "Token: ${TOKEN:0:20}..."
echo ""

echo "Test 1: Authorization Header"
echo "----------------------------"
curl -v -N -H "Authorization: Bearer $TOKEN" \
  "$URL/mcp/$TENANT/$SERVER" 2>&1 | head -30

echo ""
echo ""
echo "Test 2: Query Parameter"
echo "----------------------"
curl -v -N "$URL/mcp/$TENANT/$SERVER?token=$TOKEN" 2>&1 | head -30

echo ""
echo ""
echo "=========================================="
echo "If you see '200 OK', the token works!"
echo "If you see '403 Forbidden', check server logs"
echo "=========================================="
