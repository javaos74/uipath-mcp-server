#!/usr/bin/env python3
"""Check process keys in database."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import Database


async def main():
    """Check process keys in all tools."""
    db = Database("database/mcp_servers.db")
    await db.initialize()

    # Get all servers
    servers = await db.list_servers()
    
    print(f"\n=== Checking Process Keys in Database ===\n")
    
    for server in servers:
        print(f"Server: {server['tenant_name']}/{server['server_name']}")
        
        # Get tools for this server
        tools = await db.list_tools(server['id'])
        
        if not tools:
            print("  No tools found\n")
            continue
            
        for tool in tools:
            print(f"  Tool: {tool['name']}")
            print(f"    Process Name: {tool.get('uipath_process_name', 'N/A')}")
            print(f"    Process Key:  {tool.get('uipath_process_key', 'N/A')}")
            print(f"    Folder Path:  {tool.get('uipath_folder_path', 'N/A')}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
