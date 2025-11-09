#!/usr/bin/env python3
"""Script to add UiPath Queue monitoring tools to the database."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import Database
from src.builtin.uipath_queue import TOOLS


async def main():
    """Add UiPath Queue monitoring tools to database."""
    # Get the backend directory path
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(backend_dir, "database", "mcp_servers.db")
    
    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    db = Database(db_path)
    await db.initialize()

    print("Adding UiPath Queue monitoring tools...")

    for tool_def in TOOLS:
        try:
            # Check if tool already exists
            existing = await db.get_builtin_tool_by_name(tool_def["name"])
            
            if existing:
                print(f"✓ Tool '{tool_def['name']}' already exists (ID: {existing['id']})")
                # Update existing tool
                await db.update_builtin_tool(
                    tool_id=existing["id"],
                    description=tool_def["description"],
                    input_schema=tool_def["input_schema"],
                    python_function=f"builtin.uipath_queue.{tool_def['function'].__name__}",
                    is_active=True,
                )
                print(f"  → Updated tool definition")
            else:
                # Create new tool
                tool_id = await db.create_builtin_tool(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    input_schema=tool_def["input_schema"],
                    python_function=f"builtin.uipath_queue.{tool_def['function'].__name__}",
                )
                print(f"✓ Created tool '{tool_def['name']}' (ID: {tool_id})")

        except Exception as e:
            print(f"✗ Error adding tool '{tool_def['name']}': {e}")
            continue

    print("\nDone! UiPath Queue monitoring tools are ready to use.")
    print("\nAvailable tools:")
    for tool_def in TOOLS:
        print(f"  - {tool_def['name']}: {tool_def['description']}")


if __name__ == "__main__":
    asyncio.run(main())
