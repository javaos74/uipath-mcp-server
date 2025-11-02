#!/usr/bin/env python3
"""Test OAuth token expiration checking."""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.oauth import decode_jwt_payload, is_token_expired, get_valid_token


async def main():
    """Test token expiration functions."""
    
    # Test with a sample JWT token (this is a fake token for testing structure)
    # Real tokens from UiPath will have actual exp claims
    sample_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    
    print("Testing JWT decoding...")
    payload = decode_jwt_payload(sample_token)
    if payload:
        print(f"✅ Decoded payload: {payload}")
    else:
        print("❌ Failed to decode token")
    
    print("\nTesting token expiration check...")
    is_expired = is_token_expired(sample_token)
    print(f"Token expired: {is_expired} (expected: True, since exp is in 2018)")
    
    # Test with None token
    print("\nTesting with None token...")
    is_expired = is_token_expired(None)
    print(f"None token expired: {is_expired} (expected: True)")
    
    # Test with invalid token
    print("\nTesting with invalid token...")
    is_expired = is_token_expired("invalid.token.here")
    print(f"Invalid token expired: {is_expired} (expected: True)")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
