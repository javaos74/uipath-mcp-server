"""OAuth helper utilities for UiPath token exchange (client credentials)."""

from __future__ import annotations

import os
import logging
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
    - <base>/identity_/connect/token (Cloud)
    - <base>/identity/connect/token (On-Prem)

    Args:
        uipath_url: Full UiPath base URL configured by the user
        client_id: OAuth client id
        client_secret: OAuth client secret
        scope: Optional space-delimited scopes. Defaults to common OR scopes
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
        f"{base}/identity_/connect/token",
        f"{base}/identity/connect/token",
    ]

    effective_scope = scope or os.getenv(
        "UIPATH_OAUTH_SCOPE",
        # Read scopes for listing folders, releases, and jobs
        "OR.Folders.Read OR.Releases.Read OR.Jobs.Read",
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
                f"Requesting OAuth token via client_credentials at {endpoint}"
            )
            async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data=form,
                )

            if response.status_code == 200:
                data = response.json()
                if not data.get("access_token"):
                    raise RuntimeError(
                        "Token endpoint returned 200 but no access_token present"
                    )
                return data

            # Non-200: attempt to extract error for logs, then try next endpoint
            try:
                err = response.json()
            except Exception:
                err = {"error": response.text}
            last_error = f"HTTP {response.status_code}: {err}"
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


