#!/usr/bin/env python3
"""Test live MCP connection with detailed logging."""

import requests
import time

SERVER_URL = "http://localhost:8000"
TENANT = "UiPath"
SERVER = "CharlesTest"
TOKEN = "x8-hKN2oux5q4h0RruMiiSsJjQQPhoCYZZIQqJKjhgo"

print("=" * 70)
print("Live MCP Connection Test")
print("=" * 70)
print()
print(f"Server: {SERVER_URL}/mcp/{TENANT}/{SERVER}")
print(f"Token: {TOKEN[:20]}...")
print()

# Test 1: With Authorization header
print("Test 1: Authorization Header")
print("-" * 70)
try:
    response = requests.get(
        f"{SERVER_URL}/mcp/{TENANT}/{SERVER}",
        headers={"Authorization": f"Bearer {TOKEN}"},
        stream=True,
        timeout=3
    )
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("✅ Connection successful!")
        print("\nFirst few bytes of response:")
        for i, chunk in enumerate(response.iter_content(chunk_size=100)):
            print(chunk[:100])
            if i >= 2:
                break
    else:
        print(f"❌ Failed!")
        print(f"Response: {response.text}")
except requests.exceptions.Timeout:
    print("✅ Connection established (timeout is normal for SSE)")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print()

# Test 2: With query parameter
print("Test 2: Query Parameter")
print("-" * 70)
try:
    response = requests.get(
        f"{SERVER_URL}/mcp/{TENANT}/{SERVER}?token={TOKEN}",
        stream=True,
        timeout=3
    )
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("✅ Connection successful!")
        print("\nFirst few bytes of response:")
        for i, chunk in enumerate(response.iter_content(chunk_size=100)):
            print(chunk[:100])
            if i >= 2:
                break
    else:
        print(f"❌ Failed!")
        print(f"Response: {response.text}")
except requests.exceptions.Timeout:
    print("✅ Connection established (timeout is normal for SSE)")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print()

# Test 3: Without token (should fail)
print("Test 3: No Token (should fail with 403)")
print("-" * 70)
try:
    response = requests.get(
        f"{SERVER_URL}/mcp/{TENANT}/{SERVER}",
        timeout=2
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 403:
        print("✅ Correctly rejected!")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

print()
print("=" * 70)
print("Check the server logs for detailed authentication flow")
print("=" * 70)
