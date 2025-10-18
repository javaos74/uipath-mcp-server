"""Setup test user with UiPath configuration."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import Database


async def setup_user():
    """Setup or update test user."""
    
    db = Database("backend/database/mcp_servers.db")
    await db.initialize()
    
    print("Setting up test user 'charles'...")
    print("="*60)
    
    # Check if user exists
    user = await db.get_user_by_username("charles")
    
    if not user:
        print("Creating user 'charles'...")
        user_id = await db.create_user(
            username="charles",
            email="charles@example.com",
            password="password123",
            role="admin"
        )
        user = await db.get_user_by_id(user_id)
        print(f"✓ Created user: {user['username']} (role: {user['role']})")
    else:
        print(f"✓ User exists: {user['username']} (role: {user['role']})")
    
    # Prompt for UiPath configuration
    print("\n" + "="*60)
    print("UiPath Configuration")
    print("="*60)
    
    current_url = user.get('uipath_url')
    current_folder = user.get('uipath_folder_path')
    
    print(f"\nCurrent configuration:")
    print(f"  URL: {current_url or 'Not set'}")
    print(f"  Folder: {current_folder or 'Not set'}")
    print(f"  Token: {'Set' if user.get('uipath_access_token') else 'Not set'}")
    
    print("\nDo you want to update UiPath configuration? (y/n): ", end='')
    response = input().strip().lower()
    
    if response == 'y':
        print("\nEnter UiPath Cloud URL (e.g., https://cloud.uipath.com/account/tenant):")
        print(f"  Current: {current_url or 'Not set'}")
        print("  New (press Enter to keep current): ", end='')
        url = input().strip()
        if not url:
            url = current_url
        
        print("\nEnter UiPath Personal Access Token (PAT):")
        print("  (will not be displayed, press Enter to keep current): ", end='')
        token = input().strip()
        if not token and user.get('uipath_access_token'):
            token = None  # Keep current
        
        print("\nEnter UiPath Folder Path (e.g., /Production/Finance):")
        print(f"  Current: {current_folder or 'Not set'}")
        print("  New (press Enter to keep current): ", end='')
        folder = input().strip()
        if not folder:
            folder = current_folder
        
        # Update configuration
        await db.update_user_uipath_config(
            user_id=user['id'],
            uipath_url=url if url else None,
            uipath_access_token=token if token else None,
            uipath_folder_path=folder if folder else None
        )
        
        print("\n✓ UiPath configuration updated")
        
        # Show updated config
        user = await db.get_user_by_id(user['id'])
        print(f"\nUpdated configuration:")
        print(f"  URL: {user.get('uipath_url')}")
        print(f"  Folder: {user.get('uipath_folder_path')}")
        print(f"  Token: {'Set' if user.get('uipath_access_token') else 'Not set'}")
    
    print("\n" + "="*60)
    print("Setup completed!")
    print("\nYou can now:")
    print("  1. Login with username: charles, password: password123")
    print("  2. Test UiPath process listing:")
    print("     python backend/tests/test_uipath_processes.py")


if __name__ == "__main__":
    asyncio.run(setup_user())
