"""Test authentication and authorization."""

from starlette.testclient import TestClient
import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.http_server import app, db

# Use test database
test_db_path = "test_auth.db"
if os.path.exists(test_db_path):
    os.remove(test_db_path)

db.db_path = test_db_path

# Initialize database
asyncio.run(db.initialize())


def test_register_user():
    """Test user registration."""
    client = TestClient(app)
    
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
        "role": "user"
    }
    
    response = client.post("/auth/register", json=user_data)
    if response.status_code != 201:
        print(f"Error: {response.status_code}, {response.json()}")
    assert response.status_code == 201
    
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["role"] == "user"
    assert "hashed_password" not in data


def test_register_duplicate_user():
    """Test registering duplicate username."""
    client = TestClient(app)
    
    user_data = {
        "username": "duplicate",
        "email": "dup1@example.com",
        "password": "password123"
    }
    
    # First registration
    response1 = client.post("/auth/register", json=user_data)
    assert response1.status_code == 201
    
    # Duplicate registration
    user_data["email"] = "dup2@example.com"  # Different email
    response2 = client.post("/auth/register", json=user_data)
    assert response2.status_code == 409


def test_login():
    """Test user login."""
    client = TestClient(app)
    
    # Register user
    user_data = {
        "username": "logintest",
        "email": "login@example.com",
        "password": "password123"
    }
    client.post("/auth/register", json=user_data)
    
    # Login
    login_data = {
        "username": "logintest",
        "password": "password123"
    }
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["username"] == "logintest"


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    client = TestClient(app)
    
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 401


def test_get_current_user():
    """Test getting current user info."""
    client = TestClient(app)
    
    # Register and login
    user_data = {
        "username": "metest",
        "email": "me@example.com",
        "password": "password123"
    }
    client.post("/auth/register", json=user_data)
    
    login_response = client.post("/auth/login", json={
        "username": "metest",
        "password": "password123"
    })
    token = login_response.json()["access_token"]
    
    # Get current user
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == "metest"


def test_unauthorized_access():
    """Test accessing protected endpoint without token."""
    client = TestClient(app)
    
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_server_ownership():
    """Test that users can only access their own servers."""
    client = TestClient(app)
    
    # Create two users
    user1_data = {
        "username": "user1",
        "email": "user1@example.com",
        "password": "password123"
    }
    user2_data = {
        "username": "user2",
        "email": "user2@example.com",
        "password": "password123"
    }
    
    client.post("/auth/register", json=user1_data)
    client.post("/auth/register", json=user2_data)
    
    # Login as user1
    login1 = client.post("/auth/login", json={
        "username": "user1",
        "password": "password123"
    })
    token1 = login1.json()["access_token"]
    
    # Login as user2
    login2 = client.post("/auth/login", json={
        "username": "user2",
        "password": "password123"
    })
    token2 = login2.json()["access_token"]
    
    # User1 creates a server
    server_data = {
        "tenant_name": "user1_tenant",
        "server_name": "user1_server",
        "description": "User 1's server"
    }
    create_response = client.post(
        "/api/servers",
        json=server_data,
        headers={"Authorization": f"Bearer {token1}"}
    )
    if create_response.status_code != 201:
        print(f"Create server error: {create_response.status_code}, {create_response.json()}")
    assert create_response.status_code == 201
    
    # User1 can access their server
    get_response1 = client.get(
        "/api/servers/user1_tenant/user1_server",
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert get_response1.status_code == 200
    
    # User2 cannot access user1's server
    get_response2 = client.get(
        "/api/servers/user1_tenant/user1_server",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert get_response2.status_code == 403


def test_admin_access():
    """Test that admin can access all servers."""
    client = TestClient(app)
    
    # Create regular user and admin
    user_data = {
        "username": "regularuser",
        "email": "regular@example.com",
        "password": "password123",
        "role": "user"
    }
    admin_data = {
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "password123",
        "role": "admin"
    }
    
    client.post("/auth/register", json=user_data)
    client.post("/auth/register", json=admin_data)
    
    # Login as regular user
    login_user = client.post("/auth/login", json={
        "username": "regularuser",
        "password": "password123"
    })
    user_token = login_user.json()["access_token"]
    
    # Login as admin
    login_admin = client.post("/auth/login", json={
        "username": "adminuser",
        "password": "password123"
    })
    admin_token = login_admin.json()["access_token"]
    
    # Regular user creates a server
    server_data = {
        "tenant_name": "user_tenant",
        "server_name": "user_server",
        "description": "User's server"
    }
    client.post(
        "/api/servers",
        json=server_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    # Admin can access user's server
    get_response = client.get(
        "/api/servers/user_tenant/user_server",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200


if __name__ == "__main__":
    print("Running authentication tests...")
    print("\n" + "="*60)
    
    test_register_user()
    print("✓ Register user test passed")
    
    test_register_duplicate_user()
    print("✓ Register duplicate user test passed")
    
    test_login()
    print("✓ Login test passed")
    
    test_login_invalid_credentials()
    print("✓ Login invalid credentials test passed")
    
    test_get_current_user()
    print("✓ Get current user test passed")
    
    test_unauthorized_access()
    print("✓ Unauthorized access test passed")
    
    test_server_ownership()
    print("✓ Server ownership test passed")
    
    test_admin_access()
    print("✓ Admin access test passed")
    
    print("\n" + "="*60)
    print("All authentication tests passed! ✓")
