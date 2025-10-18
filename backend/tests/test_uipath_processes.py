"""Test UiPath process listing functionality."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import Database
from src.uipath_client import UiPathClient


async def test_list_processes():
    """Test listing UiPath processes with user credentials."""
    
    # Initialize database
    db = Database("test_uipath.db")
    await db.initialize()
    
    # Get user 'charles'
    user = await db.get_user_by_username("charles")
    
    if not user:
        print("❌ User 'charles' not found in database")
        print("Creating test user...")
        
        # Create test user
        user_id = await db.create_user(
            username="charles",
            email="charles@example.com",
            password="test123",
            role="user"
        )
        
        user = await db.get_user_by_id(user_id)
        print(f"✓ Created user: {user['username']}")
    else:
        print(f"✓ Found user: {user['username']}")
    
    # Check UiPath configuration
    print(f"\nUiPath Configuration:")
    print(f"  URL: {user.get('uipath_url')}")
    print(f"  Token: {'***' + user.get('uipath_access_token', '')[-10:] if user.get('uipath_access_token') else 'Not set'}")
    print(f"  Folder: {user.get('uipath_folder_path')}")
    
    if not user.get('uipath_url') or not user.get('uipath_access_token'):
        print("\n❌ UiPath configuration not set for user 'charles'")
        print("\nTo set configuration, run:")
        print("  1. Start the server: python -m src.main")
        print("  2. Login as 'charles'")
        print("  3. Go to Settings and configure UiPath credentials")
        return
    
    # Test listing processes
    print("\n" + "="*60)
    print("Testing UiPath process listing...")
    print("="*60)
    
    try:
        client = UiPathClient()
        processes = await client.list_processes(
            uipath_url=user['uipath_url'],
            uipath_access_token=user['uipath_access_token'],
            folder_path=user.get('uipath_folder_path')
        )
        
        print(f"\n✓ Successfully retrieved {len(processes)} processes")
        
        if processes:
            print("\nProcesses:")
            for i, process in enumerate(processes[:5], 1):  # Show first 5
                print(f"\n{i}. {process['name']}")
                print(f"   ID: {process['id']}")
                print(f"   Version: {process['version']}")
                print(f"   Description: {process['description'][:100] if process['description'] else 'N/A'}")
                print(f"   Parameters: {len(process['input_parameters'])}")
                
                if process['input_parameters']:
                    print("   Input Parameters:")
                    for param in process['input_parameters'][:3]:  # Show first 3
                        print(f"     - {param['name']} ({param['type']})")
            
            if len(processes) > 5:
                print(f"\n... and {len(processes) - 5} more processes")
        else:
            print("\n⚠ No processes found")
            print("Make sure:")
            print("  1. The UiPath URL is correct")
            print("  2. The PAT has proper permissions")
            print("  3. There are processes in the specified folder")
        
    except Exception as e:
        print(f"\n❌ Error listing processes: {str(e)}")
        print(f"\nError type: {type(e).__name__}")
        
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        
        print("\nTroubleshooting:")
        print("  1. Check if UiPath URL is correct (should be like: https://cloud.uipath.com/account/tenant)")
        print("  2. Verify PAT has 'OR.Execution' and 'OR.Folders' scopes")
        print("  3. Check if folder path is correct")
        print("  4. Ensure network connectivity to UiPath Cloud")


async def test_with_env_vars():
    """Test with environment variables (fallback)."""
    print("\n" + "="*60)
    print("Testing with environment variables...")
    print("="*60)
    
    url = os.getenv("UIPATH_URL")
    token = os.getenv("UIPATH_ACCESS_TOKEN")
    folder = os.getenv("UIPATH_FOLDER_PATH")
    
    print(f"\nEnvironment variables:")
    print(f"  UIPATH_URL: {url or 'Not set'}")
    print(f"  UIPATH_ACCESS_TOKEN: {'***' + token[-10:] if token else 'Not set'}")
    print(f"  UIPATH_FOLDER_PATH: {folder or 'Not set'}")
    
    if not url or not token:
        print("\n⚠ Environment variables not set")
        return
    
    try:
        client = UiPathClient()
        processes = await client.list_processes(
            uipath_url=url,
            uipath_access_token=token,
            folder_path=folder
        )
        
        print(f"\n✓ Successfully retrieved {len(processes)} processes using env vars")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


async def test_sdk_directly():
    """Test UiPath SDK directly."""
    print("\n" + "="*60)
    print("Testing UiPath SDK directly...")
    print("="*60)
    
    try:
        from uipath import UiPath
        
        sdk = UiPath()
        print("✓ UiPath SDK initialized")
        
        # Try to list processes
        processes = sdk.processes.list()
        print(f"✓ Retrieved processes: {type(processes)}")
        
        # Convert to list if it's an iterator
        process_list = list(processes)
        print(f"✓ Total processes: {len(process_list)}")
        
        if process_list:
            first = process_list[0]
            print(f"\nFirst process attributes:")
            for attr in dir(first):
                if not attr.startswith('_'):
                    try:
                        value = getattr(first, attr)
                        if not callable(value):
                            print(f"  {attr}: {value}")
                    except:
                        pass
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("UiPath Process Listing Test")
    print("="*60)
    
    # Run tests
    asyncio.run(test_list_processes())
    asyncio.run(test_with_env_vars())
    asyncio.run(test_sdk_directly())
    
    print("\n" + "="*60)
    print("Test completed")
