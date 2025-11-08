#!/usr/bin/env python3
"""
Add sample built-in tool to the database.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


async def add_sample_tool():
    """Add google_search sample tool."""
    db = Database()
    
    print("Initializing database...")
    await db.initialize()
    
    # Check if tool already exists
    existing = await db.get_builtin_tool_by_name("google_search")
    if existing:
        print("✓ Sample tool 'google_search' already exists")
        print(f"  ID: {existing['id']}")
        print(f"  Description: {existing['description']}")
        return
    
    # Create sample tool
    print("Creating sample built-in tool...")
    
    tool_data = {
        "name": "google_search",
        "description": "Google을 통한 검색",
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "검색 질문"
                }
            },
            "required": ["q"]
        },
        "python_function": "tools.google_search.search",
        "api_key": None  # No API key needed for this example
    }
    
    tool_id = await db.create_builtin_tool(
        name=tool_data["name"],
        description=tool_data["description"],
        input_schema=tool_data["input_schema"],
        python_function=tool_data["python_function"],
        api_key=tool_data["api_key"]
    )
    
    print(f"✓ Sample tool created successfully!")
    print(f"  ID: {tool_id}")
    print(f"  Name: {tool_data['name']}")
    print(f"  Description: {tool_data['description']}")
    print(f"  Function: {tool_data['python_function']}")
    print(f"  Parameters: q (string, required)")
    
    # Verify
    created_tool = await db.get_builtin_tool(tool_id)
    if created_tool:
        print("\n✓ Verification successful - tool is in database")
    else:
        print("\n✗ Verification failed - tool not found")


if __name__ == "__main__":
    asyncio.run(add_sample_tool())
