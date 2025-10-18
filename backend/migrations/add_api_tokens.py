#!/usr/bin/env python3
"""Add API tokens to mcp_servers table."""

import asyncio
import aiosqlite


async def migrate():
    """Add api_token column to mcp_servers table."""
    db_path = "backend/database/mcp_servers.db"
    
    async with aiosqlite.connect(db_path) as db:
        # Check if column already exists
        cursor = await db.execute("PRAGMA table_info(mcp_servers)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "api_token" not in column_names:
            print("Adding api_token column to mcp_servers table...")
            await db.execute("""
                ALTER TABLE mcp_servers 
                ADD COLUMN api_token TEXT
            """)
            await db.commit()
            print("✅ Migration completed successfully!")
        else:
            print("⚠️  Column api_token already exists, skipping migration.")


if __name__ == "__main__":
    asyncio.run(migrate())
