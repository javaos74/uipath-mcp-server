"""Reset user password script."""

import asyncio
import sys
import os
import hashlib
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import aiosqlite


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


async def reset_password(username: str, new_password: str, db_path: str):
    """Reset user password."""
    
    async with aiosqlite.connect(db_path) as db:
        # Check if user exists
        cursor = await db.execute(
            "SELECT id, username, email FROM users WHERE username = ?",
            (username,)
        )
        user = await cursor.fetchone()
        
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        # Update password
        hashed_password = hash_password(new_password)
        await db.execute(
            """
            UPDATE users 
            SET hashed_password = ?, updated_at = CURRENT_TIMESTAMP
            WHERE username = ?
            """,
            (hashed_password, username)
        )
        await db.commit()
        
        print(f"✅ Password reset for user '{username}' (ID: {user[0]})")
        return True


async def list_users(db_path: str):
    """List all users."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT id, username, email, role, is_active FROM users"
        )
        users = await cursor.fetchall()
        
        if not users:
            print("No users found")
            return
        
        print("\nUsers:")
        print("-" * 60)
        for user in users:
            status = "✓" if user[4] else "✗"
            print(f"  [{status}] {user[1]} (ID: {user[0]}, Role: {user[3]}, Email: {user[2]})")
        print()


def main():
    parser = argparse.ArgumentParser(description="Reset user password")
    parser.add_argument("username", nargs="?", help="Username to reset password for")
    parser.add_argument("password", nargs="?", help="New password")
    parser.add_argument("--db", default="database/mcp_servers.db", help="Database path")
    parser.add_argument("--list", "-l", action="store_true", help="List all users")
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_users(args.db))
        return
    
    if not args.username or not args.password:
        parser.print_help()
        print("\nExamples:")
        print("  python reset_user_password.py charles newpassword123")
        print("  python reset_user_password.py --list")
        return
    
    asyncio.run(reset_password(args.username, args.password, args.db))


if __name__ == "__main__":
    main()
