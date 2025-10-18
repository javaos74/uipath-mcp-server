#!/usr/bin/env python3
"""Add uipath_folder_id column to mcp_tools table."""

import asyncio
import aiosqlite


async def migrate():
    """Add uipath_folder_id column to mcp_tools table."""
    db_path = "backend/database/mcp_servers.db"
    
    async with aiosqlite.connect(db_path) as db:
        # Check if column already exists
        cursor = await db.execute("PRAGMA table_info(mcp_tools)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "uipath_folder_id" not in column_names:
            print("Adding uipath_folder_id column to mcp_tools table...")
            await db.execute("""
                ALTER TABLE mcp_tools 
                ADD COLUMN uipath_folder_id TEXT
            """)
            await db.commit()
            print("✅ Migration completed successfully!")
        else:
            print("⚠️  Column uipath_folder_id already exists, skipping migration.")


if __name__ == "__main__":
    asyncio.run(migrate())
