#!/usr/bin/env python3
"""Test script for UiPath Folder management tools."""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.builtin.uipath_folder import get_folders, get_folder_id_by_name


async def test_get_folders():
    """Test get_folders function."""
    print("\n" + "=" * 60)
    print("Testing: get_folders")
    print("=" * 60)
    
    uipath_url = input("Enter UiPath Orchestrator URL (e.g., https://orchestrator.local): ").strip()
    access_token = input("Enter access token: ").strip()
    folder_name = input("Enter folder name to search (optional, press Enter to skip): ").strip()
    
    if not uipath_url or not access_token:
        print("❌ URL and access token are required")
        return
    
    try:
        result = await get_folders(
            uipath_url=uipath_url,
            access_token=access_token,
            folder_name=folder_name if folder_name else None,
        )
        
        print("\n✅ Success!")
        print(f"\nFolders found: {len(result)}")
        
        print("\n📁 Folders:")
        print("-" * 80)
        for folder in result:
            print(f"  ID: {folder['id']}")
            print(f"  Name: {folder['name']}")
            print(f"  Full Name: {folder['full_name']}")
            print(f"  Type: {folder['type']}")
            print(f"  Description: {folder['description']}")
            print("-" * 80)
        
        print("\n📄 Full Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_get_folder_id_by_name():
    """Test get_folder_id_by_name function."""
    print("\n" + "=" * 60)
    print("Testing: get_folder_id_by_name")
    print("=" * 60)
    
    uipath_url = input("Enter UiPath Orchestrator URL (e.g., https://orchestrator.local): ").strip()
    access_token = input("Enter access token: ").strip()
    folder_name = input("Enter folder name to find (required): ").strip()
    
    if not uipath_url or not access_token or not folder_name:
        print("❌ URL, access token, and folder name are required")
        return
    
    try:
        result = await get_folder_id_by_name(
            uipath_url=uipath_url,
            access_token=access_token,
            folder_name=folder_name,
        )
        
        if result:
            print("\n✅ Success!")
            print(f"\nFolder '{folder_name}' found!")
            print(f"Folder ID: {result}")
        else:
            print(f"\n⚠️  Folder '{folder_name}' not found")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run tests."""
    print("\n🧪 UiPath Folder Management Tools Test")
    print("=" * 60)
    
    while True:
        print("\nSelect a test:")
        print("1. Test get_folders")
        print("2. Test get_folder_id_by_name")
        print("3. Run all tests")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "1":
            await test_get_folders()
        elif choice == "2":
            await test_get_folder_id_by_name()
        elif choice == "3":
            await test_get_folders()
            await test_get_folder_id_by_name()
        elif choice == "0":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
