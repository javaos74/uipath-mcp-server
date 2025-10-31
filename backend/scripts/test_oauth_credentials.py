#!/usr/bin/env python3
"""Test OAuth credentials for UiPath.

This script tests if the provided OAuth credentials (client_id and client_secret)
can successfully obtain an access token from UiPath Identity server.

Usage:
    python test_oauth_credentials.py

Or with environment variables:
    UIPATH_URL=https://your-server.com/org/tenant \
    UIPATH_CLIENT_ID=your-client-id \
    UIPATH_CLIENT_SECRET=your-client-secret \
    python test_oauth_credentials.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path to import oauth module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.oauth import exchange_client_credentials_for_token


async def test_oauth_credentials(
    uipath_url: str,
    client_id: str,
    client_secret: str,
    scope: str = None,
    audience: str = None,
):
    """Test OAuth credentials by attempting to get an access token.
    
    Args:
        uipath_url: UiPath base URL (e.g., https://your-server.com/org/tenant)
        client_id: OAuth Client ID
        client_secret: OAuth Client Secret
        scope: Optional OAuth scope
        audience: Optional OAuth audience
        
    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 70)
    print("UiPath OAuth Credentials Test")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  URL:       {uipath_url}")
    print(f"  Client ID: {client_id}")
    print(f"  Secret:    {'*' * min(len(client_secret), 20)}")
    if scope:
        print(f"  Scope:     {scope}")
    if audience:
        print(f"  Audience:  {audience}")
    print()
    
    try:
        print("Attempting to obtain OAuth access token...")
        print("-" * 70)
        
        token_data = await exchange_client_credentials_for_token(
            uipath_url=uipath_url,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            audience=audience,
        )
        
        print("\n✅ SUCCESS! OAuth token obtained successfully.")
        print("-" * 70)
        print("\nToken Response:")
        print(f"  Access Token: {token_data.get('access_token', '')[:50]}...")
        print(f"  Token Type:   {token_data.get('token_type', 'N/A')}")
        print(f"  Expires In:   {token_data.get('expires_in', 'N/A')} seconds")
        
        if 'scope' in token_data:
            print(f"  Scope:        {token_data.get('scope', 'N/A')}")
        
        print("\n" + "=" * 70)
        print("✅ OAuth credentials are VALID and working!")
        print("=" * 70)
        return True
        
    except ValueError as e:
        print(f"\n❌ VALIDATION ERROR: {e}")
        print("\nPlease check that all required parameters are provided.")
        return False
        
    except RuntimeError as e:
        print(f"\n❌ AUTHENTICATION FAILED: {e}")
        print("\nPossible issues:")
        print("  1. Invalid client_id or client_secret")
        print("  2. OAuth application not configured in UiPath")
        print("  3. Incorrect UiPath URL")
        print("  4. Network connectivity issues")
        print("  5. Identity server endpoint not accessible")
        return False
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False


def get_input_or_env(prompt: str, env_var: str, required: bool = True) -> str:
    """Get input from user or environment variable.
    
    Args:
        prompt: Prompt to display to user
        env_var: Environment variable name to check
        required: Whether the value is required
        
    Returns:
        str: The input value
    """
    # Check environment variable first
    value = os.getenv(env_var)
    if value:
        print(f"{prompt} (from env): {value if 'SECRET' not in env_var else '***'}")
        return value
    
    # Prompt user
    value = input(f"{prompt}: ").strip()
    
    if required and not value:
        print(f"❌ Error: {prompt} is required!")
        sys.exit(1)
    
    return value


async def main():
    """Main function to run the OAuth test."""
    print("\n" + "=" * 70)
    print("UiPath OAuth Credentials Tester")
    print("=" * 70)
    print("\nThis script will test your OAuth credentials by attempting to")
    print("obtain an access token from the UiPath Identity server.")
    print("\nYou can provide credentials via:")
    print("  1. Environment variables (UIPATH_URL, UIPATH_CLIENT_ID, UIPATH_CLIENT_SECRET)")
    print("  2. Interactive prompts (if env vars not set)")
    print()
    
    # Get credentials
    uipath_url = get_input_or_env(
        "UiPath URL (e.g., https://your-server.com/org/tenant)",
        "UIPATH_URL"
    )
    
    client_id = get_input_or_env(
        "OAuth Client ID",
        "UIPATH_CLIENT_ID"
    )
    
    client_secret = get_input_or_env(
        "OAuth Client Secret",
        "UIPATH_CLIENT_SECRET"
    )
    
    # Optional parameters
    scope = os.getenv("UIPATH_OAUTH_SCOPE")
    audience = os.getenv("UIPATH_OAUTH_AUDIENCE")
    
    # Run test
    success = await test_oauth_credentials(
        uipath_url=uipath_url,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        audience=audience,
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
