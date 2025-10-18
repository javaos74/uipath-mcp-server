"""Test server management API endpoints."""

import pytest
from starlette.testclient import TestClient
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.http_server import app, db


@pytest.fixture
async def setup_db():
    """Setup test database."""
    # Use in-memory database for testing
    db.db_path = ":memory:"
    await db.initialize()
    yield
    # Cleanup is automatic with in-memory database


def test_health_check():
    """Test health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_server():
    """Test creating a new MCP server."""
    client = TestClient(app)
    
    server_data = {
        "tenant_name": "test_tenant",
        "server_name": "test_server",
        "description": "Test MCP server"
    }
    
    response = client.post("/api/servers", json=server_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["tenant_name"] == "test_tenant"
    assert data["server_name"] == "test_server"
    assert data["description"] == "Test MCP server"
    assert "id" in data
    assert "created_at" in data


def test_list_servers():
    """Test listing all servers."""
    client = TestClient(app)
    
    # Create a server first
    server_data = {
        "tenant_name": "tenant1",
        "server_name": "server1",
        "description": "Server 1"
    }
    client.post("/api/servers", json=server_data)
    
    # List servers
    response = client.get("/api/servers")
    assert response.status_code == 200
    
    data = response.json()
    assert "count" in data
    assert "servers" in data
    assert data["count"] >= 1
    assert len(data["servers"]) >= 1


def test_get_server():
    """Test getting a specific server."""
    client = TestClient(app)
    
    # Create a server
    server_data = {
        "tenant_name": "tenant2",
        "server_name": "server2",
        "description": "Server 2"
    }
    create_response = client.post("/api/servers", json=server_data)
    assert create_response.status_code == 201
    
    # Get the server
    response = client.get("/api/servers/tenant2/server2")
    assert response.status_code == 200
    
    data = response.json()
    assert data["tenant_name"] == "tenant2"
    assert data["server_name"] == "server2"
    assert data["description"] == "Server 2"


def test_get_nonexistent_server():
    """Test getting a server that doesn't exist."""
    client = TestClient(app)
    
    response = client.get("/api/servers/nonexistent/server")
    assert response.status_code == 404
    assert "error" in response.json()


def test_update_server():
    """Test updating a server."""
    client = TestClient(app)
    
    # Create a server
    server_data = {
        "tenant_name": "tenant3",
        "server_name": "server3",
        "description": "Original description"
    }
    client.post("/api/servers", json=server_data)
    
    # Update the server
    update_data = {
        "description": "Updated description"
    }
    response = client.put("/api/servers/tenant3/server3", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["description"] == "Updated description"


def test_delete_server():
    """Test deleting a server."""
    client = TestClient(app)
    
    # Create a server
    server_data = {
        "tenant_name": "tenant4",
        "server_name": "server4",
        "description": "To be deleted"
    }
    client.post("/api/servers", json=server_data)
    
    # Delete the server
    response = client.delete("/api/servers/tenant4/server4")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get("/api/servers/tenant4/server4")
    assert get_response.status_code == 404


def test_create_duplicate_server():
    """Test creating a server with duplicate tenant/server name."""
    client = TestClient(app)
    
    server_data = {
        "tenant_name": "tenant5",
        "server_name": "server5",
        "description": "First server"
    }
    
    # Create first server
    response1 = client.post("/api/servers", json=server_data)
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post("/api/servers", json=server_data)
    assert response2.status_code == 409
    assert "error" in response2.json()


def test_create_multiple_servers():
    """Test creating multiple servers."""
    client = TestClient(app)
    
    servers = [
        {"tenant_name": "prod", "server_name": "finance", "description": "Finance automation"},
        {"tenant_name": "prod", "server_name": "hr", "description": "HR automation"},
        {"tenant_name": "dev", "server_name": "test", "description": "Test server"},
    ]
    
    for server_data in servers:
        response = client.post("/api/servers", json=server_data)
        assert response.status_code == 201
    
    # List all servers
    response = client.get("/api/servers")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 3


if __name__ == "__main__":
    print("Running server management tests...")
    print("\n" + "="*60)
    
    # Run tests manually
    test_health_check()
    print("✓ Health check test passed")
    
    test_create_server()
    print("✓ Create server test passed")
    
    test_list_servers()
    print("✓ List servers test passed")
    
    test_get_server()
    print("✓ Get server test passed")
    
    test_get_nonexistent_server()
    print("✓ Get nonexistent server test passed")
    
    test_update_server()
    print("✓ Update server test passed")
    
    test_delete_server()
    print("✓ Delete server test passed")
    
    test_create_duplicate_server()
    print("✓ Create duplicate server test passed")
    
    test_create_multiple_servers()
    print("✓ Create multiple servers test passed")
    
    print("\n" + "="*60)
    print("All tests passed! ✓")
