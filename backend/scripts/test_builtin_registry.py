#!/usr/bin/env python3
"""Test script for built-in tools auto-registration system."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import Database
from src.builtin_registry import discover_builtin_tools, register_builtin_tools


async def main():
    """Test the built-in tools registry system."""
    print("=" * 60)
    print("Built-in Tools Auto-Registration Test")
    print("=" * 60)
    print()
    
    # Test 1: Discover tools
    print("Test 1: Discovering built-in tools...")
    print("-" * 60)
    tools = await discover_builtin_tools()
    print(f"\nDiscovered {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool['name']}")
    print()
    
    # Test 2: Register tools to database
    print("Test 2: Registering tools to database...")
    print("-" * 60)
    
    # Create database directory if it doesn't exist
    os.makedirs("database", exist_ok=True)
    
    db = Database("database/mcp_servers.db")
    await db.initialize()
    
    # Check current version
    current_version = await db.get_builtin_tools_version()
    print(f"Current version in DB: {current_version}")
    
    # Reset version to 0 to force re-registration (for testing)
    await db.set_builtin_tools_version(0)
    print("Reset version to 0 for testing...")
    
    # Register tools
    count = await register_builtin_tools(db)
    print(f"\nRegistered/Updated: {count} tools")
    
    # Check new version
    new_version = await db.get_builtin_tools_version()
    print(f"New version in DB: {new_version}")
    print()
    
    # Test 3: List registered tools
    print("Test 3: Listing registered tools from database...")
    print("-" * 60)
    registered_tools = await db.list_builtin_tools(active_only=False)
    print(f"\nFound {len(registered_tools)} tools in database:")
    for tool in registered_tools:
        status = "✓" if tool["is_active"] else "✗"
        print(f"  {status} {tool['name']} (ID: {tool['id']})")
        print(f"    Function: {tool['python_function']}")
    print()
    
    # Test 4: Test idempotency (run registration again)
    print("Test 4: Testing idempotency (running registration again)...")
    print("-" * 60)
    count2 = await register_builtin_tools(db)
    print(f"Second run registered: {count2} tools (should be 0)")
    print()
    
    print("=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
