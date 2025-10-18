#!/usr/bin/env python3
"""Test token API endpoints."""

import requests
import sys

SERVER_URL = "http://localhost:8000"

def test_token_api():
    """Test token generation, retrieval, and revocation."""
    
    print("=" * 60)
    print("Token API Test")
    print("=" * 60)
    print()
    
    # Step 1: Login
    print("Step 1: Login...")
    username = input("Username: ")
    password = input("Password: ")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        auth_token = response.json()["access_token"]
        print(f"✅ Login successful!")
        print()
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return
    
    # Get server info
    tenant_name = input("Tenant name (e.g., UiPath): ")
    server_name = input("Server name (e.g., CharlesTest): ")
    print()
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Step 2: Check existing token
    print("Step 2: Checking existing token...")
    try:
        response = requests.get(
            f"{SERVER_URL}/api/servers/{tenant_name}/{server_name}/token",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("token"):
            print(f"✅ Existing token found: {data['token'][:20]}...")
        else:
            print("ℹ️  No token exists yet")
        print()
    except Exception as e:
        print(f"❌ Failed to check token: {e}")
        print()
    
    # Step 3: Generate new token
    print("Step 3: Generating new token...")
    try:
        response = requests.post(
            f"{SERVER_URL}/api/servers/{tenant_name}/{server_name}/token",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        api_token = data["token"]
        
        print(f"✅ Token generated successfully!")
        print(f"Token: {api_token}")
        print()
    except Exception as e:
        print(f"❌ Failed to generate token: {e}")
        return
    
    # Step 4: Retrieve token
    print("Step 4: Retrieving token...")
    try:
        response = requests.get(
            f"{SERVER_URL}/api/servers/{tenant_name}/{server_name}/token",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        if data["token"] == api_token:
            print(f"✅ Token retrieved successfully!")
            print(f"Token matches: {data['token'][:20]}...")
        else:
            print(f"⚠️  Token mismatch!")
        print()
    except Exception as e:
        print(f"❌ Failed to retrieve token: {e}")
        print()
    
    # Step 5: Test MCP connection with token
    print("Step 5: Testing MCP connection with generated token...")
    try:
        response = requests.get(
            f"{SERVER_URL}/mcp/{tenant_name}/{server_name}?token={api_token}",
            stream=True,
            timeout=3
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ MCP connection successful with API token!")
        else:
            print(f"❌ MCP connection failed: {response.text}")
        print()
    except requests.exceptions.Timeout:
        print("✅ Connection established (timeout is normal for SSE)")
        print()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
    
    # Step 6: Revoke token
    revoke = input("Do you want to revoke the token? (y/n): ")
    if revoke.lower() == 'y':
        print("\nStep 6: Revoking token...")
        try:
            response = requests.delete(
                f"{SERVER_URL}/api/servers/{tenant_name}/{server_name}/token",
                headers=headers
            )
            response.raise_for_status()
            print("✅ Token revoked successfully!")
            print()
        except Exception as e:
            print(f"❌ Failed to revoke token: {e}")
            print()
    
    print("=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_token_api()
