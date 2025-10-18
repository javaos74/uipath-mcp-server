"""Test tool management API endpoints."""

import pytest
from starlette.testclient import TestClient
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.http_server import app, db


def test_create_tool():
    """Test creating a new tool."""
    client = TestClient(app)
    
    # Create a server first
    server_data = {
        "tenant_name": "test",
        "server_name": "tools_test",
        "description": "Test server for tools"
    }
    client.post("/api/servers", json=server_data)
    
    # Create a tool
    tool_data = {
        "name": "test_tool",
        "description": "A test tool",
        "input_schema": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "First parameter"
                }
            },
            "required": ["param1"]
        },
        "uipath_process_name": "TestProcess",
        "uipath_folder_path": "/Test"
    }
    
    response = client.post("/api/servers/test/tools_test/tools", json=tool_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "test_tool"
    assert data["description"] == "A test tool"
    assert "input_schema" in data
    assert data["uipath_process_name"] == "TestProcess"


def test_list_tools():
    """Test listing tools for a server."""
    client = TestClient(app)
    
    # Create a server
    server_data = {
        "tenant_name": "test2",
        "server_name": "list_test",
        "description": "Test server"
    }
    client.post("/api/servers", json=server_data)
    
    # Create multiple tools
    tools = [
        {
            "name": "tool1",
            "description": "Tool 1",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "tool2",
            "description": "Tool 2",
            "input_schema": {"type": "object", "properties": {}}
        }
    ]
    
    for tool in tools:
        client.post("/api/servers/test2/list_test/tools", json=tool)
    
    # List tools
    response = client.get("/api/servers/test2/list_test/tools")
    assert response.status_code == 200
    
    data = response.json()
    assert "count" in data
    assert "tools" in data
    assert data["count"] == 2


def test_get_tool():
    """Test getting a specific tool."""
    client = TestClient(app)
    
    # Create server and tool
    server_data = {
        "tenant_name": "test3",
        "server_name": "get_test",
        "description": "Test server"
    }
    client.post("/api/servers", json=server_data)
    
    tool_data = {
        "name": "specific_tool",
        "description": "Specific tool",
        "input_schema": {
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            }
        }
    }
    client.post("/api/servers/test3/get_test/tools", json=tool_data)
    
    # Get the tool
    response = client.get("/api/servers/test3/get_test/tools/specific_tool")
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "specific_tool"
    assert data["description"] == "Specific tool"


def test_update_tool():
    """Test updating a tool."""
    client = TestClient(app)
    
    # Create server and tool
    server_data = {
        "tenant_name": "test4",
        "server_name": "update_test",
        "description": "Test server"
    }
    client.post("/api/servers", json=server_data)
    
    tool_data = {
        "name": "update_tool",
        "description": "Original description",
        "input_schema": {"type": "object", "properties": {}}
    }
    client.post("/api/servers/test4/update_test/tools", json=tool_data)
    
    # Update the tool
    update_data = {
        "description": "Updated description",
        "uipath_process_name": "NewProcess"
    }
    response = client.put("/api/servers/test4/update_test/tools/update_tool", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["uipath_process_name"] == "NewProcess"


def test_delete_tool():
    """Test deleting a tool."""
    client = TestClient(app)
    
    # Create server and tool
    server_data = {
        "tenant_name": "test5",
        "server_name": "delete_test",
        "description": "Test server"
    }
    client.post("/api/servers", json=server_data)
    
    tool_data = {
        "name": "delete_tool",
        "description": "To be deleted",
        "input_schema": {"type": "object", "properties": {}}
    }
    client.post("/api/servers/test5/delete_test/tools", json=tool_data)
    
    # Delete the tool
    response = client.delete("/api/servers/test5/delete_test/tools/delete_tool")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get("/api/servers/test5/delete_test/tools/delete_tool")
    assert get_response.status_code == 404


def test_tool_with_complex_schema():
    """Test creating a tool with complex input schema."""
    client = TestClient(app)
    
    # Create server
    server_data = {
        "tenant_name": "test6",
        "server_name": "complex_test",
        "description": "Test server"
    }
    client.post("/api/servers", json=server_data)
    
    # Create tool with complex schema
    tool_data = {
        "name": "complex_tool",
        "description": "Tool with complex schema",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "User name"
                },
                "age": {
                    "type": "number",
                    "description": "User age"
                },
                "active": {
                    "type": "boolean",
                    "description": "Is active"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags"
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"}
                    }
                }
            },
            "required": ["name", "age"]
        }
    }
    
    response = client.post("/api/servers/test6/complex_test/tools", json=tool_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "complex_tool"
    assert "properties" in data["input_schema"]
    assert len(data["input_schema"]["properties"]) == 5


if __name__ == "__main__":
    print("Running tool management tests...")
    print("\n" + "="*60)
    
    test_create_tool()
    print("✓ Create tool test passed")
    
    test_list_tools()
    print("✓ List tools test passed")
    
    test_get_tool()
    print("✓ Get tool test passed")
    
    test_update_tool()
    print("✓ Update tool test passed")
    
    test_delete_tool()
    print("✓ Delete tool test passed")
    
    test_tool_with_complex_schema()
    print("✓ Complex schema test passed")
    
    print("\n" + "="*60)
    print("All tests passed! ✓")
