"""OAuth helper utilities for UiPath token exchange (client credentials)."""

from __future__ import annotations

import os
import logging
import base64
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import httpx


logger = logging.getLogger(__name__)


async def exchange_client_credentials_for_token(
    uipath_url: str,
    client_id: str,
    client_secret: str,
    scope: Optional[str] = None,
    audience: Optional[str] = None,
) -> Dict[str, Any]:
    """Exchange OAuth client credentials for an access token.

    This attempts UiPath Identity endpoints commonly used in Cloud and On-Prem:
    - <base>/identity_/connect/token (Cloud & Automation Suite)
    - <base>/<org_name>/identity/connect/token (On-Prem MSI)

    Args:
        uipath_url: Full UiPath base URL configured by the user
        client_id: OAuth client id
        client_secret: OAuth client secret
        scope: Optional space-delimited scopes. set empty to use scope when it generated 
        audience: Optional audience parameter (e.g. orchestrator)

    Returns:
        Parsed token response JSON (must contain access_token)
    """
    if not uipath_url or not client_id or not client_secret:
        raise ValueError("uipath_url, client_id and client_secret are required")

    parsed = urlparse(uipath_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Endpoints to try (Cloud first, then On-Prem style)
    token_endpoints = [
        f"{base}/identity/connect/token",  # for MSI on-premise 
        f"{base}/identity_/connect/token", # for cloud & automation suite 
    ]

    # Not used  just use scope which specified at external application 
    effective_scope = scope or os.getenv(
        "UIPATH_OAUTH_SCOPE",
        # Read scopes for listing folders, releases, and jobs
        "OR.Jobs OR.Folders OR.Execution",
    )
    effective_audience = audience or os.getenv(
        "UIPATH_OAUTH_AUDIENCE",
        "https://orchestrator.uipath.com",
    )

    form: Dict[str, Any] = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": effective_scope,
    }

    # Only include audience if set; some servers reject unknown params
    if effective_audience:
        form["audience"] = effective_audience

    last_error: Optional[str] = None

    for endpoint in token_endpoints:
        try:
            logger.info(
                f"Requesting OAuth token via client_credentials at {endpoint} with scope: {effective_scope}"
            )
            async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data=form,
                )

            logger.info(f"OAuth token request response: HTTP {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if not data.get("access_token"):
                    raise RuntimeError(
                        "Token endpoint returned 200 but no access_token present"
                    )
                logger.info("Successfully obtained OAuth access token")
                return data

            # Non-200: attempt to extract error for logs, then try next endpoint
            try:
                err = response.json()
                error_detail = err.get("error_description", err.get("error", response.text))
            except Exception:
                error_detail = response.text
            last_error = f"HTTP {response.status_code}: {error_detail}"
            logger.warning(
                f"Token request to {endpoint} failed: {last_error}; trying fallback"
            )

        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                f"Token request to {endpoint} raised exception: {last_error}; trying fallback"
            )

    raise RuntimeError(
        f"Failed to obtain OAuth token from Identity endpoints. Last error: {last_error}"
    )



def decode_jwt_payload(token: str) -> Optional[Dict[str, Any]]:
    """Decode JWT token payload without verification.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dictionary or None if decoding fails
    """
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            logger.warning("Invalid JWT format: expected 3 parts")
            return None
        
        # Decode payload (second part)
        payload = parts[1]
        
        # Add padding if needed (JWT base64 may not have padding)
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        # Decode base64
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded_json = json.loads(decoded_bytes)
        
        return decoded_json
        
    except Exception as e:
        logger.warning(f"Failed to decode JWT token: {e}")
        return None


def is_token_expired(token: str, buffer_seconds: int = 60) -> bool:
    """Check if OAuth access token (JWT) is expired or will expire soon.
    
    Note: This only works for JWT tokens (OAuth). PAT tokens cannot be checked
    and will return False (assume valid until 401 error occurs).
    
    Args:
        token: JWT access token
        buffer_seconds: Consider token expired if it expires within this many seconds (default: 60)
        
    Returns:
        True if token is expired or will expire soon, False if valid or cannot be decoded (PAT)
    """
    if not token:
        return True
    
    payload = decode_jwt_payload(token)
    if not payload:
        # Could not decode - likely a PAT token, not JWT
        # Return False to allow it to be used (will fail with 401 if actually expired)
        logger.debug("Token is not JWT format (likely PAT), cannot check expiration")
        return False
    
    # Check expiration time (exp claim)
    exp = payload.get('exp')
    if not exp:
        # JWT without exp claim - treat as non-expiring
        logger.debug("JWT token has no 'exp' claim, treating as valid")
        return False
    
    try:
        # exp is Unix timestamp
        expiration_time = datetime.fromtimestamp(exp, tz=timezone.utc)
        current_time = datetime.now(timezone.utc)
        
        # Add buffer to prevent using tokens that are about to expire
        from datetime import timedelta
        expiration_with_buffer = expiration_time - timedelta(seconds=buffer_seconds)
        
        is_expired = current_time >= expiration_with_buffer
        
        if is_expired:
            logger.info(f"OAuth token expired or expiring soon (exp: {expiration_time.isoformat()}, now: {current_time.isoformat()})")
        else:
            time_until_expiry = expiration_time - current_time
            logger.debug(f"OAuth token valid for {time_until_expiry.total_seconds():.0f} more seconds")
        
        return is_expired
        
    except Exception as e:
        logger.warning(f"Error checking token expiration: {e}")
        return False  # Assume valid if we can't check


async def get_valid_token(
    current_token: Optional[str],
    uipath_url: str,
    client_id: str,
    client_secret: str,
) -> str:
    """Get a valid access token, refreshing if necessary.
    
    This is a convenience function that checks if the current token is valid,
    and if not, exchanges credentials for a new token.
    
    Args:
        current_token: Current access token (may be None or expired)
        uipath_url: UiPath base URL
        client_id: OAuth client ID
        client_secret: OAuth client secret
        
    Returns:
        Valid access token
        
    Raises:
        RuntimeError: If token exchange fails
    """
    # Check if current token is valid
    if current_token and not is_token_expired(current_token):
        logger.debug("Current token is still valid")
        return current_token
    
    # Token is missing or expired, get a new one
    logger.info("Token is missing or expired, requesting new token")
    token_response = await exchange_client_credentials_for_token(
        uipath_url=uipath_url,
        client_id=client_id,
        client_secret=client_secret,
    )
    
    new_token = token_response.get("access_token")
    if not new_token:
        raise RuntimeError("Token response did not contain access_token")
    
    return new_token
