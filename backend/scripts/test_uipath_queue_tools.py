#!/usr/bin/env python3
"""Test script for UiPath Queue monitoring tools."""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.builtin.uipath_queue import get_queues_health_state, get_queues_table


async def test_get_queues_health_state():
    """Test get_queues_health_state function."""
    print("\n" + "=" * 60)
    print("Testing: get_queues_health_state")
    print("=" * 60)
    
    uipath_url = input("Enter UiPath Orchestrator URL (e.g., https://orchestrator.local): ").strip()
    access_token = input("Enter access token: ").strip()
    time_frame = input("Enter time frame in minutes (default: 1440 = 24 hours): ").strip()
    
    if not uipath_url or not access_token:
        print("❌ URL and access token are required")
        return
    
    time_frame_minutes = int(time_frame) if time_frame else 1440
    
    try:
        result = await get_queues_health_state(
            uipath_url=uipath_url,
            access_token=access_token,
            time_frame_minutes=time_frame_minutes,
        )
        
        print("\n✅ Success!")
        print(f"\nQueues found: {len(result.get('data', []))}")
        print(f"Timestamp: {result.get('timeStamp', 'N/A')}")
        
        print("\n📊 Queues Health State:")
        print("-" * 60)
        for item in result.get('data', []):
            queue_data = item.get('data', {})
            print(f"  Queue: {queue_data.get('queueName', 'N/A')}")
            print(f"    Folder: {queue_data.get('fullyQualifiedName', 'N/A')}")
            print(f"    Health State: {queue_data.get('healthState', 'N/A')}")
            print()
        
        print("\n📄 Full Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_get_queues_table():
    """Test get_queues_table function."""
    print("\n" + "=" * 60)
    print("Testing: get_queues_table")
    print("=" * 60)
    
    uipath_url = input("Enter UiPath Orchestrator URL (e.g., https://orchestrator.local): ").strip()
    access_token = input("Enter access token: ").strip()
    time_frame = input("Enter time frame in minutes (default: 1440 = 24 hours): ").strip()
    page_size = input("Enter page size (default: 10): ").strip()
    
    if not uipath_url or not access_token:
        print("❌ URL and access token are required")
        return
    
    time_frame_minutes = int(time_frame) if time_frame else 1440
    page_size_int = int(page_size) if page_size else 100
    
    try:
        result = await get_queues_table(
            uipath_url=uipath_url,
            access_token=access_token,
            time_frame_minutes=time_frame_minutes,
            page_no=1,
            page_size=page_size_int,
        )
        
        print("\n✅ Success!")
        print(f"\nTotal Queues: {result.get('total', 0)}")
        print(f"Queues in current page: {len(result.get('data', []))}")
        
        print("\n📊 Queues Table:")
        print("-" * 120)
        print(f"{'Queue Name':<30} {'Total':>8} {'Deferred':>10} {'Overdue':>10} {'In SLA':>10} {'AHT (s)':>10}")
        print("-" * 120)
        
        for queue in result.get('data', []):
            print(f"{queue['queueName']:<30} "
                  f"{queue['countTotal']:>8} "
                  f"{queue['countDeferred']:>10} "
                  f"{queue['countOverdue']:>10} "
                  f"{queue['countInSLA']:>10} "
                  f"{queue['ahtSeconds']:>10.2f}")
        
        print("\n📄 Full Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run tests."""
    print("\n🧪 UiPath Queue Monitoring Tools Test")
    print("=" * 60)
    
    while True:
        print("\nSelect a test:")
        print("1. Test get_queues_health_state")
        print("2. Test get_queues_table")
        print("3. Run all tests")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "1":
            await test_get_queues_health_state()
        elif choice == "2":
            await test_get_queues_table()
        elif choice == "3":
            await test_get_queues_health_state()
            await test_get_queues_table()
        elif choice == "0":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
