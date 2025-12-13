"""Manually register built-in tools immediately."""
import asyncio
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database
from src.builtin_registry import register_builtin_tools, discover_builtin_tools, BUILTIN_TOOLS_VERSION


async def main():
    """Register built-in tools."""
    db_path = Path(__file__).parent.parent / "database" / "mcp_servers.db"
    print(f"Using database: {db_path}")
    db = Database(str(db_path))
    
    # Check current version
    current_version = await db.get_builtin_tools_version()
    print(f"Current DB version: {current_version}")
    print(f"Target version: {BUILTIN_TOOLS_VERSION}")
    
    # Discover tools first
    print("\nDiscovering tools...")
    tools = await discover_builtin_tools()
    print(f"Found {len(tools)} tools")
    
    # Register
    print("\nForcing registration...")
    count = await register_builtin_tools(db)
    print(f"\n✅ Registered/Updated {count} tools")
    
    # Check new version
    new_version = await db.get_builtin_tools_version()
    print(f"New DB version: {new_version}")


if __name__ == "__main__":
    asyncio.run(main())
