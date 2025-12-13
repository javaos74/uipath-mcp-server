"""Check registered built-in tools in database."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


async def main():
    """Check built-in tools."""
    db_path = Path(__file__).parent.parent / "database" / "mcp_servers.db"
    db = Database(str(db_path))
    
    # Check version
    version = await db.get_builtin_tools_version()
    print(f"📌 Current version: {version}")
    
    # Get all builtin tools
    import aiosqlite
    async with aiosqlite.connect(str(db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT name, is_active FROM builtin_tools ORDER BY name"
        )
        tools = await cursor.fetchall()
    
    print(f"\n📋 Registered tools: {len(tools)}")
    print("-" * 60)
    
    for tool in tools:
        status = "✅" if tool["is_active"] else "❌"
        print(f"{status} {tool['name']}")
    
    # Check for storage bucket tools
    storage_tools = [t for t in tools if "storage" in t["name"].lower()]
    print(f"\n🪣 Storage bucket tools: {len(storage_tools)}")
    for tool in storage_tools:
        status = "✅" if tool["is_active"] else "❌"
        print(f"{status} {tool['name']}")


if __name__ == "__main__":
    asyncio.run(main())
