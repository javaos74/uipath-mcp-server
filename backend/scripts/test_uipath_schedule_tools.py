#!/usr/bin/env python3
"""Test script for UiPath Schedule monitoring tools."""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.builtin.uipath_schedule import get_process_schedules


async def test_get_process_schedules():
    """Test get_process_schedules function."""
    print("\n" + "=" * 60)
    print("Testing: get_process_schedules")
    print("=" * 60)
    
    uipath_url = input("Enter UiPath Orchestrator URL (e.g., https://orchestrator.local): ").strip()
    access_token = input("Enter access token: ").strip()
    org_unit_id = input("Enter organization unit ID (folder ID): ").strip()
    top = input("Enter max number of schedules (default: 100): ").strip()
    
    if not uipath_url or not access_token or not org_unit_id:
        print("❌ URL, access token, and organization unit ID are required")
        return
    
    top_int = int(top) if top else 100
    
    try:
        result = await get_process_schedules(
            uipath_url=uipath_url,
            access_token=access_token,
            organization_unit_id=int(org_unit_id),
            top=top_int,
        )
        
        print("\n✅ Success!")
        print(f"\nSchedules found: {len(result)}")
        
        print("\n📅 Process Schedules:")
        print("-" * 100)
        print(f"{'Name':<30} {'Enabled':<10} {'Release':<30} {'Schedule':<20}")
        print("-" * 100)
        
        for schedule in result:
            enabled_str = "✓ Yes" if schedule['enabled'] else "✗ No"
            print(f"{schedule['name']:<30} "
                  f"{enabled_str:<10} "
                  f"{schedule['release_name']:<30} "
                  f"{schedule['cron_summary']:<20}")
        
        print("\n📄 Full Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run tests."""
    print("\n🧪 UiPath Schedule Monitoring Tools Test")
    print("=" * 60)
    
    while True:
        print("\nSelect a test:")
        print("1. Test get_process_schedules")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "1":
            await test_get_process_schedules()
        elif choice == "0":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
