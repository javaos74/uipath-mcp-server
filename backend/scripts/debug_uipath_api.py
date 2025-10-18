"""Debug UiPath API call to see actual error."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import Database
from src.uipath_client import UiPathClient


async def debug_api_call():
    """Debug the actual API call that's failing."""
    
    print("Debugging UiPath API Call")
    print("="*60)
    
    # Get user from database
    db = Database("backend/database/mcp_servers.db")
    await db.initialize()
    
    user = await db.get_user_by_username("charles")
    
    if not user:
        print("❌ User 'charles' not found")
        print("\nRun this first:")
        print("  python backend/scripts/setup_test_user.py")
        return
    
    print(f"✓ Found user: {user['username']}")
    
    # Check configuration
    url = user.get('uipath_url')
    token = user.get('uipath_access_token')
    folder = user.get('uipath_folder_path')
    
    print(f"\nConfiguration:")
    print(f"  URL: {url or 'NOT SET'}")
    print(f"  Token: {'SET (' + token[:10] + '...' + token[-5:] + ')' if token else 'NOT SET'}")
    print(f"  Folder: {folder or 'NOT SET'}")
    
    if not url or not token:
        print("\n❌ UiPath configuration incomplete")
        print("\nRun this to configure:")
        print("  python backend/scripts/setup_test_user.py")
        return
    
    # Try to call the API
    print("\n" + "="*60)
    print("Calling UiPath API...")
    print("="*60)
    
    try:
        client = UiPathClient()
        
        print("\n1. Initializing SDK...")
        sdk = client._get_sdk(url, token)
        print("   ✓ SDK initialized")
        
        print("\n2. Setting folder path...")
        if folder:
            os.environ["UIPATH_FOLDER_PATH"] = folder
            print(f"   ✓ Folder set to: {folder}")
        else:
            print("   ⚠ No folder path set")
        
        print("\n3. Listing processes...")
        processes = sdk.processes.list()
        print(f"   ✓ Got response: {type(processes)}")
        
        print("\n4. Converting to list...")
        process_list = list(processes)
        print(f"   ✓ Total processes: {len(process_list)}")
        
        if process_list:
            print("\n5. Examining first process...")
            first = process_list[0]
            print(f"   Type: {type(first)}")
            print(f"   Attributes: {[a for a in dir(first) if not a.startswith('_')]}")
            
            print("\n6. Extracting process info...")
            info = {
                "id": str(first.id) if hasattr(first, "id") else "N/A",
                "name": str(first.name) if hasattr(first, "name") else "N/A",
                "description": str(first.description) if hasattr(first, "description") else "N/A",
                "version": str(first.version) if hasattr(first, "version") else "N/A",
                "key": str(first.key) if hasattr(first, "key") else "N/A",
            }
            
            print(f"   Process info:")
            for key, value in info.items():
                print(f"     {key}: {value}")
            
            print("\n7. Checking for arguments...")
            if hasattr(first, "arguments"):
                print(f"   Arguments type: {type(first.arguments)}")
                print(f"   Arguments value: {first.arguments}")
            else:
                print("   ⚠ No 'arguments' attribute")
            
            # Try to get all attributes
            print("\n8. All process attributes:")
            for attr in dir(first):
                if not attr.startswith('_') and not callable(getattr(first, attr, None)):
                    try:
                        value = getattr(first, attr)
                        print(f"     {attr}: {value}")
                    except Exception as e:
                        print(f"     {attr}: Error - {e}")
        
        print("\n" + "="*60)
        print("✓ API call successful!")
        print(f"✓ Found {len(process_list)} processes")
        
    except Exception as e:
        print(f"\n❌ Error occurred!")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        
        import traceback
        print("\n   Full traceback:")
        print("   " + "\n   ".join(traceback.format_exc().split("\n")))
        
        print("\n" + "="*60)
        print("Troubleshooting:")
        print("  1. Verify UiPath URL format: https://cloud.uipath.com/account/tenant")
        print("  2. Check PAT permissions: OR.Execution, OR.Folders, OR.Robots")
        print("  3. Verify folder path exists and is accessible")
        print("  4. Test PAT in UiPath Cloud UI first")


if __name__ == "__main__":
    asyncio.run(debug_api_call())
