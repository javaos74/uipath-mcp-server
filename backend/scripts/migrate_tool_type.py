#!/usr/bin/env python3
"""
Migration script to set tool_type='uipath' for existing tools.

This script can be run manually to migrate existing database records.
It's also automatically run during database initialization.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


async def migrate():
    """Run migration to set default tool_type for existing tools."""
    db = Database()
    
    print("Starting migration...")
    
    # Initialize database (this will run the migration)
    await db.initialize()
    
    # Check results
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        # Count tools by type
        cursor = await conn.execute(
            """
            SELECT 
                tool_type,
                COUNT(*) as count
            FROM mcp_tools
            GROUP BY tool_type
            """
        )
        rows = await cursor.fetchall()
        
        print("\nMigration complete!")
        print("\nTools by type:")
        for row in rows:
            tool_type = row[0] or "NULL"
            count = row[1]
            print(f"  {tool_type}: {count}")
        
        # Check for any NULL values
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM mcp_tools WHERE tool_type IS NULL"
        )
        null_count = await cursor.fetchone()
        
        if null_count and null_count[0] > 0:
            print(f"\n⚠️  Warning: {null_count[0]} tools still have NULL tool_type")
        else:
            print("\n✅ All tools have valid tool_type")


if __name__ == "__main__":
    asyncio.run(migrate())
