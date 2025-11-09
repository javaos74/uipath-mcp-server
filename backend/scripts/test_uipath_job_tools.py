#!/usr/bin/env python3
"""Test script for UiPath Job monitoring tools."""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.builtin.uipath_job import get_jobs_stats, get_finished_jobs_evolution, get_processes_table


async def test_get_jobs_stats():
    """Test get_jobs_stats function."""
    print("\n" + "=" * 60)
    print("Testing: get_jobs_stats")
    print("=" * 60)
    
    # You need to provide your UiPath Orchestrator URL and access token
    uipath_url = input("Enter UiPath Orchestrator URL (e.g., https://orchestrator.local): ").strip()
    access_token = input("Enter access token: ").strip()
    
    if not uipath_url or not access_token:
        print("❌ URL and access token are required")
        return
    
    try:
        result = await get_jobs_stats(
            uipath_url=uipath_url,
            access_token=access_token,
        )
        
        print("\n✅ Success!")
        print(f"\nTotal Jobs: {result['total']}")
        print("\nJob Statistics by Status:")
        print("-" * 60)
        for stat in result['stats']:
            print(f"  {stat['title']:15} : {stat['count']:5} jobs")
        
        print("\n📄 Full Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_get_finished_jobs_evolution():
    """Test get_finished_jobs_evolution function."""
    print("\n" + "=" * 60)
    print("Testing: get_finished_jobs_evolution")
    print("=" * 60)
    
    # You need to provide your UiPath Orchestrator URL and access token
    uipath_url = input("Enter UiPath Orchestrator URL (e.g., https://orchestrator.local): ").strip()
    access_token = input("Enter access token: ").strip()
    time_frame = input("Enter time frame in minutes (default: 1440 = 24 hours): ").strip()
    
    if not uipath_url or not access_token:
        print("❌ URL and access token are required")
        return
    
    time_frame_minutes = int(time_frame) if time_frame else 1440
    
    try:
        result = await get_finished_jobs_evolution(
            uipath_url=uipath_url,
            access_token=access_token,
            time_frame_minutes=time_frame_minutes,
        )
        
        print("\n✅ Success!")
        print(f"\nTime Frame: {time_frame_minutes} minutes")
        print(f"Data Points: {len(result)}")
        
        # Calculate summary statistics
        total_successful = sum(item.get("countSuccessful", 0) for item in result)
        total_errors = sum(item.get("countErrors", 0) for item in result)
        total_stopped = sum(item.get("countStopped", 0) for item in result)
        
        print("\nSummary:")
        print("-" * 60)
        print(f"  Total Successful: {total_successful}")
        print(f"  Total Errors    : {total_errors}")
        print(f"  Total Stopped   : {total_stopped}")
        print(f"  Total           : {total_successful + total_errors + total_stopped}")
        
        print("\n📊 Evolution Data (last 5 points):")
        print("-" * 60)
        for point in result[-5:]:
            print(f"  {point['pointInTime']}")
            print(f"    Successful: {point['countSuccessful']}, Errors: {point['countErrors']}, Stopped: {point['countStopped']}")
        
        print("\n📄 Full Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_get_processes_table():
    """Test get_processes_table function."""
    print("\n" + "=" * 60)
    print("Testing: get_processes_table")
    print("=" * 60)
    
    # You need to provide your UiPath Orchestrator URL and access token
    uipath_url = input("Enter UiPath Orchestrator URL (e.g., https://orchestrator.local): ").strip()
    access_token = input("Enter access token: ").strip()
    time_frame = input("Enter time frame in minutes (default: 1440 = 24 hours): ").strip()
    page_size = input("Enter page size (default: 100): ").strip()
    
    if not uipath_url or not access_token:
        print("❌ URL and access token are required")
        return
    
    time_frame_minutes = int(time_frame) if time_frame else 1440
    page_size_int = int(page_size) if page_size else 100
    
    try:
        result = await get_processes_table(
            uipath_url=uipath_url,
            access_token=access_token,
            time_frame_minutes=time_frame_minutes,
            page_no=1,
            page_size=page_size_int,
        )
        
        print("\n✅ Success!")
        print(f"\nTotal Processes: {result.get('total', 0)}")
        print(f"Processes in current page: {len(result.get('data', []))}")
        
        print("\n📊 Processes Table:")
        print("-" * 120)
        print(f"{'Process Name':<30} {'Successful':>10} {'Errors':>10} {'Stopped':>10} {'Running':>10} {'Avg Duration':>15}")
        print("-" * 120)
        
        for process in result.get('data', []):
            avg_duration = process.get('averageDurationInSeconds')
            avg_duration_str = f"{avg_duration}s" if avg_duration is not None else "N/A"
            
            print(f"{process['processName']:<30} "
                  f"{process['countSuccessful']:>10} "
                  f"{process['countErrors']:>10} "
                  f"{process['countStopped']:>10} "
                  f"{process['countExecuting']:>10} "
                  f"{avg_duration_str:>15}")
        
        print("\n📄 Full Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run tests."""
    print("\n🧪 UiPath Job Monitoring Tools Test")
    print("=" * 60)
    
    while True:
        print("\nSelect a test:")
        print("1. Test get_jobs_stats")
        print("2. Test get_finished_jobs_evolution")
        print("3. Test get_processes_table")
        print("4. Run all tests")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "1":
            await test_get_jobs_stats()
        elif choice == "2":
            await test_get_finished_jobs_evolution()
        elif choice == "3":
            await test_get_processes_table()
        elif choice == "4":
            await test_get_jobs_stats()
            await test_get_finished_jobs_evolution()
            await test_get_processes_table()
        elif choice == "0":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
