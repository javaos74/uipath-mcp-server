#!/usr/bin/env python3
"""Script to reset builtin_tools table and add only 2 UiPath tools."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import Database


async def main():
    """Reset builtin_tools table and add 2 UiPath tools."""
    # Get the backend directory path
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(backend_dir, "database", "mcp_servers.db")
    
    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    db = Database(db_path)
    await db.initialize()

    print("Resetting builtin_tools table...")
    
    # Delete all existing builtin tools
    import aiosqlite
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("DELETE FROM builtin_tools")
        deleted_count = cursor.rowcount
        await conn.commit()
        print(f"✓ Deleted {deleted_count} existing tools")

    print("\nAdding 2 UiPath monitoring tools...")

    # Tool 1: uipath_get_jobs_stats
    tool1_id = await db.create_builtin_tool(
        name="uipath_get_jobs_stats",
        description="Get job statistics from UiPath Orchestrator showing counts by status (Successful, Faulted, Stopped, Running, Pending, etc.)",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        },
        python_function="builtin.uipath_job.get_jobs_stats",
    )
    print(f"✓ Created tool 'uipath_get_jobs_stats' (ID: {tool1_id})")

    # Tool 2: uipath_get_queues_table
    tool2_id = await db.create_builtin_tool(
        name="uipath_get_queues_table",
        description="Get a paginated table of queues with statistics including item counts, SLA status, average handling time, and estimated completion time",
        input_schema={
            "type": "object",
            "properties": {
                "time_frame_minutes": {
                    "type": "integer",
                    "description": "Time frame in minutes (default: 1440 = 24 hours)",
                    "default": 1440
                },
                "page_no": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of items per page (default: 100)",
                    "default": 100
                },
                "organization_unit_id": {
                    "type": "integer",
                    "description": "Organization unit ID (optional)"
                }
            },
            "required": []
        },
        python_function="builtin.uipath_queue.get_queues_table",
    )
    print(f"✓ Created tool 'uipath_get_queues_table' (ID: {tool2_id})")

    print("\nDone! 2 UiPath monitoring tools are ready to use.")
    print("\nAvailable tools:")
    print("  1. uipath_get_jobs_stats - Get job statistics by status")
    print("  2. uipath_get_queues_table - Get queue statistics table")


if __name__ == "__main__":
    asyncio.run(main())
