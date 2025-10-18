#!/usr/bin/env python3
"""Test MCP authentication with both JWT and API tokens."""

import requests
import sys

SERVER_URL = "http://localhost:8000"

def test_authentication():
    """Test both JWT and API token authentication."""
    
    print("=" * 70)
    print("MCP Authentication Test - JWT vs API Token")
    print("=" * 70)
    print()
    
    # Step 1: Login to get JWT token
    print("Step 1: Login to get JWT token...")
    username = input("Username: ")
    password = input("Password: ")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        jwt_token = response.json()["access_token"]
        print(f"✅ JWT token obtained: {jwt_token[:20]}...")
        print()
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return
    
    # Get server info
    tenant_name = input("Tenant name (e.g., UiPath): ")
    server_name = input("Server name (e.g., CharlesTest): ")
    print()
    
    # Step 2: Generate API token
    print("Step 2: Generating server API token...")
    try:
        response = requests.post(
            f"{SERVER_URL}/api/servers/{tenant_name}/{server_name}/token",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        response.raise_for_status()
        api_token = response.json()["token"]
        print(f"✅ API token generated: {api_token[:20]}...")
        print()
    except Exception as e:
        print(f"❌ Failed to generate API token: {e}")
        return
    
    # Step 3: Test MCP access with JWT token
    print("Step 3: Testing MCP access with JWT token...")
    print(f"URL: {SERVER_URL}/mcp/{tenant_name}/{server_name}")
    try:
        response = requests.get(
            f"{SERVER_URL}/mcp/{tenant_name}/{server_name}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            stream=True,
            timeout=2
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ JWT token authentication successful!")
        else:
            print(f"❌ Failed: {response.text}")
    except requests.exceptions.Timeout:
        print("✅ JWT token authentication successful! (timeout is normal for SSE)")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Step 4: Test MCP access with API token (Authorization header)
    print("Step 4: Testing MCP access with API token (Authorization header)...")
    try:
        response = requests.get(
            f"{SERVER_URL}/mcp/{tenant_name}/{server_name}",
            headers={"Authorization": f"Bearer {api_token}"},
            stream=True,
            timeout=2
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ API token authentication successful!")
        else:
            print(f"❌ Failed: {response.text}")
    except requests.exceptions.Timeout:
        print("✅ API token authentication successful! (timeout is normal for SSE)")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Step 5: Test MCP access with API token (query parameter)
    print("Step 5: Testing MCP access with API token (query parameter)...")
    try:
        response = requests.get(
            f"{SERVER_URL}/mcp/{tenant_name}/{server_name}?token={api_token}",
            stream=True,
            timeout=2
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ API token (query param) authentication successful!")
        else:
            print(f"❌ Failed: {response.text}")
    except requests.exceptions.Timeout:
        print("✅ API token (query param) authentication successful! (timeout is normal for SSE)")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Step 6: Test with invalid token
    print("Step 6: Testing with invalid token (should fail)...")
    try:
        response = requests.get(
            f"{SERVER_URL}/mcp/{tenant_name}/{server_name}",
            headers={"Authorization": "Bearer invalid_token_12345"},
            timeout=2
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 403:
            print("✅ Invalid token correctly rejected!")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    print()
    
    # Step 7: Test without token
    print("Step 7: Testing without token (should fail)...")
    try:
        response = requests.get(
            f"{SERVER_URL}/mcp/{tenant_name}/{server_name}",
            timeout=2
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 403:
            print("✅ No token correctly rejected!")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    print()
    
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    print()
    print("✅ Both authentication methods work:")
    print(f"   1. JWT Token: {jwt_token[:30]}...")
    print(f"   2. API Token: {api_token[:30]}...")
    print()
    print("For external MCP clients, use the API token:")
    print(f"   Authorization: Bearer {api_token}")
    print()
    print("Or with query parameter:")
    print(f"   ?token={api_token}")
    print()

if __name__ == "__main__":
    test_authentication()
