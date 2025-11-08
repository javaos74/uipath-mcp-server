#!/usr/bin/env python3
"""
Test built-in tool execution.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.builtin.executor import execute_builtin_tool


async def test_google_search():
    """Test google_search built-in tool."""
    print("=" * 60)
    print("Testing google_search built-in tool")
    print("=" * 60)
    
    # Test 1: Simplified path without API key
    print("\n[Test 1] Executing with simplified path (google_search.google_search)...")
    result = await execute_builtin_tool(
        python_function="google_search.google_search",  # Simplified!
        arguments={"q": "Python programming"},
        api_key=None
    )
    print(f"Result: {result}")
    
    # Test 2: Simplified path with mock API key
    print("\n[Test 2] Executing with mock API key...")
    result = await execute_builtin_tool(
        python_function="google_search.google_search",  # Simplified!
        arguments={"q": "Machine Learning"},
        api_key="MOCK_API_KEY_12345"
    )
    print(f"Result: {result}")
    
    # Test 3: Full path (backward compatibility)
    print("\n[Test 3] Testing full path (backward compatibility)...")
    result = await execute_builtin_tool(
        python_function="src.builtin.google_search.google_search",  # Full path
        arguments={"q": "AI Technology"},
        api_key="MOCK_API_KEY_12345"
    )
    print(f"Result: {result}")
    
    # Test 4: Invalid function path
    print("\n[Test 4] Testing error handling (invalid function)...")
    result = await execute_builtin_tool(
        python_function="nonexistent.function",  # Simplified invalid path
        arguments={"q": "test"},
        api_key=None
    )
    print(f"Result: {result}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_google_search())
