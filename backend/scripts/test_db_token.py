#!/usr/bin/env python3
"""Test database token retrieval."""

import asyncio
import sys

sys.path.insert(0, "backend/src")

from database import Database


async def test_token():
    """Test token retrieval from database."""

    db = Database("backend/database/mcp_servers.db")

    tenant_name = "UiPath"
    server_name = "CharlesTest"

    print(f"Testing token retrieval for: {tenant_name}/{server_name}")
    print()

    # Get server
    server = await db.get_server(tenant_name, server_name)
    print(f"Server: {server}")
    print()

    # Get token
    token = await db.get_server_token(tenant_name, server_name)
    print(f"Token from get_server_token(): {token}")
    print()

    if token:
        print(f"✅ Token retrieved successfully!")
        print(f"   Length: {len(token)}")
        print(f"   First 20 chars: {token[:20]}")
        print(f"   Last 10 chars: {token[-10:]}")
    else:
        print(f"❌ No token found!")


if __name__ == "__main__":
    asyncio.run(test_token())
