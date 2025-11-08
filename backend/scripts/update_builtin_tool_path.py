#!/usr/bin/env python3
"""
Update existing built-in tool python_function path to simplified format.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


async def update_tool_path():
    """Update google_search tool to use simplified path."""
    db = Database()
    
    print("Initializing database...")
    await db.initialize()
    
    # Get existing tool
    tool = await db.get_builtin_tool_by_name("google_search")
    if not tool:
        print("✗ Tool 'google_search' not found")
        return
    
    print(f"Current python_function: {tool['python_function']}")
    
    # Update to simplified path
    new_path = "google_search.google_search"
    
    if tool['python_function'] == new_path:
        print("✓ Tool already uses simplified path")
        return
    
    print(f"Updating to: {new_path}")
    
    success = await db.update_builtin_tool(
        tool_id=tool['id'],
        python_function=new_path
    )
    
    if success:
        print("✓ Successfully updated python_function path")
        
        # Verify
        updated_tool = await db.get_builtin_tool(tool['id'])
        print(f"Verified: {updated_tool['python_function']}")
    else:
        print("✗ Failed to update")


if __name__ == "__main__":
    asyncio.run(update_tool_path())
