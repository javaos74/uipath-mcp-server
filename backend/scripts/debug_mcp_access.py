#!/usr/bin/env python3
"""Debug MCP access issues."""

import asyncio
import sys
sys.path.insert(0, 'backend/src')

from database import Database

async def debug_access():
    """Debug MCP access configuration."""
    
    db = Database("backend/database/mcp_servers.db")
    
    print("=" * 70)
    print("MCP Access Debug Tool")
    print("=" * 70)
    print()
    
    # Get server info
    tenant_name = input("Tenant name (e.g., UiPath): ").strip()
    server_name = input("Server name (e.g., CharlesTest): ").strip()
    print()
    
    # Check if server exists
    print(f"1. Checking if server exists: {tenant_name}/{server_name}")
    server = await db.get_server(tenant_name, server_name)
    
    if not server:
        print(f"❌ Server not found!")
        print(f"   Please check the tenant_name and server_name")
        print()
        
        # List available servers
        print("Available servers:")
        servers = await db.list_servers()
        for s in servers:
            print(f"   - {s['tenant_name']}/{s['server_name']} (owner: user_id={s['user_id']})")
        return
    
    print(f"✅ Server found!")
    print(f"   ID: {server['id']}")
    print(f"   Owner: user_id={server['user_id']}")
    print(f"   Description: {server.get('description', 'N/A')}")
    print()
    
    # Check if server has API token
    print(f"2. Checking server API token...")
    server_token = await db.get_server_token(tenant_name, server_name)
    
    if server_token:
        print(f"✅ Server has API token configured")
        print(f"   Token: {server_token[:20]}...{server_token[-10:]}")
        print(f"   Length: {len(server_token)} characters")
    else:
        print(f"❌ Server has NO API token configured")
        print(f"   You need to generate a token in the web UI")
    print()
    
    # Check users
    print(f"3. Checking users who can access this server...")
    
    # Get owner
    owner = await db.get_user_by_id(server['user_id'])
    if owner:
        print(f"✅ Owner: {owner['username']} (id={owner['id']}, role={owner['role']})")
    else:
        print(f"⚠️  Owner user not found (id={server['user_id']})")
    
    # Get all users
    print()
    print("All users:")
    # We need to query users manually
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT id, username, role, is_active FROM users")
        users = await cursor.fetchall()
        
        for user in users:
            access = "❌"
            reason = ""
            
            if user['role'] == 'admin':
                access = "✅"
                reason = "(admin - can access all servers)"
            elif user['id'] == server['user_id']:
                access = "✅"
                reason = "(owner)"
            else:
                reason = "(not owner)"
            
            print(f"   {access} {user['username']} (id={user['id']}, role={user['role']}) {reason}")
    
    print()
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    print()
    
    if server_token:
        print("✅ Server API Token is configured")
        print(f"   Use this token to access: {server_token}")
        print()
        print("   Test with curl:")
        print(f"   curl -N -H 'Authorization: Bearer {server_token}' \\")
        print(f"     http://localhost:8000/mcp/{tenant_name}/{server_name}")
        print()
        print("   Or with query parameter:")
        print(f"   curl -N 'http://localhost:8000/mcp/{tenant_name}/{server_name}?token={server_token}'")
    else:
        print("❌ Server API Token is NOT configured")
        print()
        print("   To generate a token:")
        print("   1. Login to web UI")
        print(f"   2. Go to server detail page: {tenant_name}/{server_name}")
        print("   3. Click 'Generate Token' in API Token section")
    
    print()
    
    if owner:
        print(f"✅ Owner can access with JWT token")
        print(f"   Login as: {owner['username']}")
        print()
        print("   Get JWT token:")
        print(f"   curl -X POST http://localhost:8000/auth/login \\")
        print(f"     -H 'Content-Type: application/json' \\")
        print(f"     -d '{{\"username\":\"{owner['username']}\",\"password\":\"YOUR_PASSWORD\"}}'")

if __name__ == "__main__":
    asyncio.run(debug_access())
