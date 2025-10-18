#!/usr/bin/env python3
"""Test MCP endpoint authentication."""

import requests
import sys

# Configuration
SERVER_URL = "http://localhost:8000"
TENANT_NAME = "UiPath"
SERVER_NAME = "CharlesTest"

def test_mcp_connection():
    """Test MCP endpoint with authentication."""
    
    print("=" * 60)
    print("MCP Authentication Test")
    print("=" * 60)
    print()
    
    # Step 1: Login
    print("Step 1: Getting access token...")
    username = input("Username: ")
    password = input("Password: ")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        print(f"✅ Login successful!")
        print(f"Token: {token[:20]}...")
        print()
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return
    
    # Step 2: Test with Authorization header
    print("Step 2: Testing with Authorization header...")
    mcp_url = f"{SERVER_URL}/mcp/{TENANT_NAME}/{SERVER_NAME}"
    print(f"URL: {mcp_url}")
    
    try:
        response = requests.get(
            mcp_url,
            headers={"Authorization": f"Bearer {token}"},
            stream=True,
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Connection successful!")
            print("Response headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
        elif response.status_code == 403:
            print("❌ 403 Forbidden - Access denied")
            print("Possible reasons:")
            print("  1. Server doesn't exist")
            print("  2. You don't own this server")
            print("  3. Token is invalid")
            print(f"Response: {response.text}")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.Timeout:
        print("⚠️  Request timed out (this might be normal for SSE)")
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    print()
    
    # Step 3: Test with query parameter
    print("Step 3: Testing with query parameter...")
    mcp_url_with_token = f"{SERVER_URL}/mcp/{TENANT_NAME}/{SERVER_NAME}?token={token}"
    print(f"URL: {mcp_url_with_token[:80]}...")
    
    try:
        response = requests.get(
            mcp_url_with_token,
            stream=True,
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Connection successful!")
        elif response.status_code == 403:
            print("❌ 403 Forbidden - Access denied")
            print(f"Response: {response.text}")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.Timeout:
        print("⚠️  Request timed out (this might be normal for SSE)")
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    print()
    print("=" * 60)
    print("Test completed!")
    print("=" * 60)
    print()
    print("To use in MCP clients:")
    print()
    print("Method 1 - Authorization Header (Recommended):")
    print(f"  URL: {SERVER_URL}/mcp/{TENANT_NAME}/{SERVER_NAME}")
    print(f"  Header: Authorization: Bearer {token}")
    print()
    print("Method 2 - Query Parameter:")
    print(f"  URL: {SERVER_URL}/mcp/{TENANT_NAME}/{SERVER_NAME}?token={token}")
    print()

if __name__ == "__main__":
    test_mcp_connection()
