"""HTTP Streamable (SSE) server for MCP with authentication."""

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, Response, FileResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http import StreamableHTTPServerTransport
import json
import logging
import os
import anyio
import asyncio
from pathlib import Path
from datetime import timedelta
from typing import Optional

from .mcp_server import DynamicMCPServer
from .database import Database

# Configure logging
logger = logging.getLogger(__name__)
from .auth import (
    create_access_token,
    get_current_user,
    check_server_ownership,
    check_mcp_access,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .models import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    UiPathConfigUpdate,
    ServerCreate,
    ServerUpdate,
    ToolCreate,
    ToolUpdate,
    BuiltinToolCreate,
    BuiltinToolUpdate,
)
from .oauth import exchange_client_credentials_for_token, get_valid_token, get_valid_token


# No-op ASGI callable for handlers that already sent response
class NoOpResponse:
    """ASGI callable that does nothing (response already sent)."""

    async def __call__(self, scope, receive, send):
        pass


# Initialize database
import os

db_path = os.getenv("DB_PATH", "database/mcp_servers.db")
db = Database(db_path)

# Store MCP server instances per endpoint
mcp_servers = {}

# Store SSE transports per endpoint
sse_transports = {}

# Store Streamable HTTP transports and background tasks per endpoint
streamable_transports = {}
streamable_tasks = {}

# Lightweight init coordination (best-effort) to reduce race on first request
sse_init_started = {}
streamable_init_started = {}
streamable_started_at = {}


def _mask_authorization(headers: dict) -> dict:
    try:
        masked = dict(headers)
        auth = masked.get("authorization") or masked.get("Authorization")
        if auth and isinstance(auth, str):
            parts = auth.split()
            if len(parts) == 2:
                token = parts[1]
                masked_token = token[:6] + "..." if len(token) > 6 else "***"
                masked["Authorization"] = f"Bearer {masked_token}"
        return masked
    except Exception:
        return headers


async def startup():
    """Initialize on startup."""
    logger.info("Initializing HTTP server and database...")
    await db.initialize()
    logger.info("HTTP server startup complete")


async def get_or_create_mcp_server(
    tenant_name: str, server_name: str
) -> DynamicMCPServer:
    """Get or create MCP server instance for endpoint."""
    key = f"{tenant_name}/{server_name}"

    if key not in mcp_servers:
        logger.info(f"Creating new MCP server instance for {key}")
        server_data = await db.get_server(tenant_name, server_name)
        if not server_data:
            logger.warning(f"Server not found: {key}")
            return None

        # Pass user_id to MCP server for UiPath credentials
        mcp_server = DynamicMCPServer(
            server_data["id"], db, user_id=server_data["user_id"]
        )
        await mcp_server.initialize()
        mcp_servers[key] = mcp_server
        logger.info(f"MCP server instance created for {key}")
    else:
        logger.debug(f"Using cached MCP server instance for {key}")

    return mcp_servers[key]


# ==================== Authentication Endpoints ====================


async def register(request):
    """Register a new user (pending approval)."""
    try:
        data = await request.json()
        user_data = UserCreate(**data)
        logger.info(f"Registration attempt for username: {user_data.username}")

        # Check if username exists
        existing = await db.get_user_by_username(user_data.username)
        if existing:
            logger.warning(
                f"Registration failed: username {user_data.username} already exists"
            )
            return JSONResponse({"error": "Username already exists"}, status_code=409)

        # Create user with is_active=0 (pending approval)
        user_id = await db.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role="user",  # Always create as user, admin can change later
        )

        # Set is_active to 0 (pending approval)
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE users SET is_active = 0 WHERE id = ?",
                (user_id,),
            )
            await conn.commit()

        logger.info(
            f"User registered successfully (pending approval): {user_data.username} (id={user_id})"
        )
        
        return JSONResponse({
            "message": "Registration successful. Your account is pending administrator approval.",
            "username": user_data.username
        }, status_code=201)

    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


async def login(request):
    """Login and get access token."""
    try:
        data = await request.json()
        login_data = UserLogin(**data)
        logger.info(f"Login attempt for username: {login_data.username}")

        # Get user
        user = await db.get_user_by_username(login_data.username)
        if not user:
            logger.warning(f"Login failed: user not found - {login_data.username}")
            return JSONResponse(
                {"error": "Invalid username or password"}, status_code=401
            )

        # Verify password
        if not db.verify_password(login_data.password, user["hashed_password"]):
            logger.warning(f"Login failed: invalid password for {login_data.username}")
            return JSONResponse(
                {"error": "Invalid username or password"}, status_code=401
            )

        # Check if active (0 = pending approval, 1 = approved/active)
        if not user["is_active"]:
            logger.warning(f"Login failed: account not approved - {login_data.username}")
            return JSONResponse(
                {"error": "Your account is pending administrator approval"}, status_code=403
            )

        # Create access token
        access_token = create_access_token(
            data={"sub": user["username"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        user_data = {
            k: v
            for k, v in user.items()
            if k
            not in ["hashed_password", "uipath_access_token", "uipath_client_secret"]
        }
        user_data["has_uipath_token"] = bool(user.get("uipath_access_token"))
        user_data["has_oauth_credentials"] = bool(
            user.get("uipath_client_id") and user.get("uipath_client_secret")
        )
        user_response = UserResponse(**user_data)

        token_response = Token(access_token=access_token, user=user_response)

        logger.info(f"Login successful: {login_data.username}")
        return JSONResponse(token_response.model_dump())

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


async def get_me(request):
    """Get current user info."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Exclude sensitive data and add token status
    user_data = {
        k: v
        for k, v in user.model_dump().items()
        if k not in ["hashed_password", "uipath_access_token", "uipath_client_secret"]
    }
    user_data["has_uipath_token"] = bool(user.uipath_access_token)
    user_data["has_oauth_credentials"] = bool(
        user.uipath_client_id and user.uipath_client_secret
    )
    user_response = UserResponse(**user_data)
    return JSONResponse(user_response.model_dump())


async def update_uipath_config(request):
    """Update current user's UiPath configuration."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    try:
        data = await request.json()
        logger.info(f"Received UiPath config update: {data}")
        config = UiPathConfigUpdate(**data)

        logger.info(
            f"Parsed config - auth_type: {config.uipath_auth_type}, "
            f"client_id: {config.uipath_client_id}, "
            f"has_client_secret: {bool(config.uipath_client_secret)}"
        )

        # First persist any provided fields
        await db.update_user_uipath_config(
            user_id=user.id,
            uipath_url=config.uipath_url,
            uipath_auth_type=config.uipath_auth_type,
            uipath_access_token=config.uipath_access_token,
            uipath_client_id=config.uipath_client_id,
            uipath_client_secret=config.uipath_client_secret,
        )

        # If switching to OAuth and we have credentials, exchange for access token
        oauth_error_message = None
        try:
            if (config.uipath_auth_type == "oauth") or (
                not config.uipath_auth_type and user.uipath_auth_type == "oauth"
            ):
                # Fetch fresh user data to ensure we have stored values
                current = await db.get_user_by_id(user.id)
                uipath_url = config.uipath_url or current.get("uipath_url")
                client_id = config.uipath_client_id or current.get("uipath_client_id")
                client_secret = config.uipath_client_secret or current.get(
                    "uipath_client_secret"
                )

                logger.info(
                    f"OAuth token exchange attempt - URL: {uipath_url}, Client ID: {client_id}, Has Secret: {bool(client_secret)}"
                )

                if uipath_url and client_id and client_secret:
                    try:
                        token_resp = await exchange_client_credentials_for_token(
                            uipath_url=uipath_url,
                            client_id=client_id,
                            client_secret=client_secret,
                        )
                        access_token = token_resp.get("access_token")
                        if access_token:
                            await db.update_user_uipath_config(
                                user_id=user.id,
                                uipath_access_token=access_token,
                            )
                            logger.info(
                                "Successfully stored OAuth access token for user"
                            )
                        else:
                            oauth_error_message = (
                                "Token response did not contain access_token"
                            )
                            logger.error(
                                f"OAuth token exchange failed: {oauth_error_message}"
                            )
                    except Exception as token_error:
                        oauth_error_message = str(token_error)
                        logger.error(
                            f"OAuth token exchange failed: {oauth_error_message}"
                        )
                else:
                    missing_fields = []
                    if not uipath_url:
                        missing_fields.append("URL")
                    if not client_id:
                        missing_fields.append("Client ID")
                    if not client_secret:
                        missing_fields.append("Client Secret")
                    oauth_error_message = (
                        f"Missing required fields: {', '.join(missing_fields)}"
                    )
                    logger.info(
                        f"OAuth selected but missing fields; skipping token exchange: {oauth_error_message}"
                    )
        except Exception as e:
            # Don't fail the save entirely; report error in response below
            oauth_error_message = str(e)
            logger.warning(f"OAuth token exchange failed: {e}")

        # Get updated user
        updated_user = await db.get_user_by_id(user.id)
        user_data = {
            k: v
            for k, v in updated_user.items()
            if k
            not in ["hashed_password", "uipath_access_token", "uipath_client_secret"]
        }
        user_data["has_uipath_token"] = bool(updated_user.get("uipath_access_token"))
        user_data["has_oauth_credentials"] = bool(
            updated_user.get("uipath_client_id")
            and updated_user.get("uipath_client_secret")
        )
        user_response = UserResponse(**user_data)

        resp = user_response.model_dump()
        # If the token is missing after an OAuth attempt, include a detailed hint
        if (config.uipath_auth_type == "oauth") and not updated_user.get(
            "uipath_access_token"
        ):
            # Emit an error log to aid debugging when token wasn't minted
            logger.error(
                "OAuth token not generated after save (auth_type=%s, has_url=%s, has_client_id=%s, has_client_secret=%s)",
                updated_user.get("uipath_auth_type"),
                bool(updated_user.get("uipath_url")),
                bool(updated_user.get("uipath_client_id")),
                bool(updated_user.get("uipath_client_secret")),
            )
            if oauth_error_message:
                resp["message"] = (
                    f"OAuth credentials saved but token exchange failed: {oauth_error_message}"
                )
            else:
                resp["message"] = (
                    "OAuth credentials saved. Token exchange did not complete; "
                    "ensure URL and client credentials are correct."
                )

        return JSONResponse(resp)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def change_password(request):
    """Change current user's password."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    try:
        data = await request.json()
        from .models import PasswordChange
        password_data = PasswordChange(**data)

        # Update password
        success = await db.update_user_password(
            user_id=user.id,
            old_password=password_data.old_password,
            new_password=password_data.new_password,
        )

        if not success:
            logger.warning(f"Password change failed for user {user.username}: incorrect old password")
            return JSONResponse(
                {"error": "Current password is incorrect"}, status_code=400
            )

        logger.info(f"Password changed successfully for user {user.username}")
        return JSONResponse({"message": "Password changed successfully"})

    except Exception as e:
        logger.error(f"Password change error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


async def _ensure_valid_oauth_token(user_id: int) -> Optional[str]:
    """Ensure user has a valid OAuth token, refreshing proactively if needed.
    
    This function checks if the token is expired BEFORE making API calls,
    preventing 401 errors. Only works for OAuth authentication.
    
    Args:
        user_id: User ID
        
    Returns:
        Valid access token if OAuth is configured, None otherwise
    """
    from .oauth import get_valid_token
    
    # Get user data
    user_data = await db.get_user_by_id(user_id)
    if not user_data:
        return None
    
    # Only handle OAuth tokens
    if user_data.get("uipath_auth_type") != "oauth":
        # PAT mode - return existing token as-is
        return user_data.get("uipath_access_token")
    
    # Check if we have OAuth credentials
    uipath_url = user_data.get("uipath_url")
    client_id = user_data.get("uipath_client_id")
    client_secret = user_data.get("uipath_client_secret")
    current_token = user_data.get("uipath_access_token")
    
    if not all([uipath_url, client_id, client_secret]):
        logger.warning("OAuth mode but missing credentials")
        return current_token
    
    try:
        # Get valid token (will refresh if expired)
        valid_token = await get_valid_token(
            current_token=current_token,
            uipath_url=uipath_url,
            client_id=client_id,
            client_secret=client_secret,
        )
        
        # Update DB if token changed
        if valid_token != current_token:
            await db.update_user_uipath_config(
                user_id=user_id,
                uipath_access_token=valid_token,
            )
            logger.info(f"Proactively refreshed OAuth token for user {user_id}")
        
        return valid_token
        
    except Exception as e:
        logger.error(f"Failed to ensure valid OAuth token: {e}")
        return current_token  # Return current token and let it fail naturally


async def _refresh_oauth_token_if_needed(
    user_id: int, error_message: str
) -> Optional[str]:
    """Refresh OAuth token if 401 error detected (reactive fallback).
    
    This is a fallback for when proactive refresh didn't happen or failed.
    Only works for OAuth authentication.

    Args:
        user_id: User ID
        error_message: Error message from API call

    Returns:
        New access token if refreshed, None otherwise
    """
    # Check if error is 401 Unauthorized
    if "401" not in error_message and "Unauthorized" not in error_message:
        return None

    logger.info(
        f"Detected 401 error, attempting to refresh OAuth token for user {user_id}"
    )

    # Get user data
    user_data = await db.get_user_by_id(user_id)
    if not user_data:
        return None

    # Only refresh if using OAuth (PAT cannot be refreshed)
    if user_data.get("uipath_auth_type") != "oauth":
        logger.info("User is using PAT, cannot refresh token - user must update manually")
        return None

    # Check if we have OAuth credentials
    uipath_url = user_data.get("uipath_url")
    client_id = user_data.get("uipath_client_id")
    client_secret = user_data.get("uipath_client_secret")

    if not all([uipath_url, client_id, client_secret]):
        logger.warning("Missing OAuth credentials, cannot refresh token")
        return None

    try:
        # Exchange credentials for new token
        token_resp = await exchange_client_credentials_for_token(
            uipath_url=uipath_url,
            client_id=client_id,
            client_secret=client_secret,
        )

        new_token = token_resp.get("access_token")
        if new_token:
            # Update token in database
            await db.update_user_uipath_config(
                user_id=user_id,
                uipath_access_token=new_token,
            )
            logger.info(f"Successfully refreshed OAuth token for user {user_id}")
            return new_token
        else:
            logger.error("Token response did not contain access_token")
            return None

    except Exception as e:
        logger.error(f"Failed to refresh OAuth token: {e}")
        return None


async def list_uipath_folders(request):
    """List UiPath folders using current user's credentials."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Get user's UiPath credentials
    user_data = await db.get_user_by_id(user.id)
    if not user_data.get("uipath_url"):
        return JSONResponse(
            {"error": "UiPath configuration not set. Please configure in Settings."},
            status_code=400,
        )

    # Proactively ensure valid token (OAuth only, PAT passes through)
    valid_token = await _ensure_valid_oauth_token(user.id)
    if not valid_token:
        return JSONResponse(
            {"error": "UiPath access token not configured. Please configure in Settings."},
            status_code=400,
        )

    try:
        from .uipath_client import UiPathClient

        client = UiPathClient()
        # Optional search query parameter
        q = request.query_params.get("q")
        # Server-side search request (if provided)
        matched = []
        if q:
            matched = await client.list_folders(
                uipath_url=user_data["uipath_url"],
                uipath_access_token=valid_token,
                search=q,
            )

        # Always also return the full list as today
        folders = await client.list_folders(
            uipath_url=user_data["uipath_url"],
            uipath_access_token=valid_token,
        )

        return JSONResponse(
            {
                "count": len(folders),
                "folders": folders,
                # Provide optional matched list if q present
                **({"matched": matched, "matched_count": len(matched)} if q else {}),
            }
        )

    except Exception as e:
        error_msg = str(e)

        # Try to refresh token if 401 error
        new_token = await _refresh_oauth_token_if_needed(user.id, error_msg)

        if new_token:
            # Retry with new token
            try:
                matched = []
                if q:
                    matched = await client.list_folders(
                        uipath_url=user_data["uipath_url"],
                        uipath_access_token=new_token,
                        search=q,
                    )

                folders = await client.list_folders(
                    uipath_url=user_data["uipath_url"],
                    uipath_access_token=new_token,
                )

                return JSONResponse(
                    {
                        "count": len(folders),
                        "folders": folders,
                        **(
                            {"matched": matched, "matched_count": len(matched)}
                            if q
                            else {}
                        ),
                    }
                )
            except Exception as retry_error:
                return JSONResponse({"error": str(retry_error)}, status_code=500)

        return JSONResponse({"error": error_msg}, status_code=500)


async def list_uipath_processes(request):
    """List UiPath processes in a specific folder using current user's credentials."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Get folder_id from query parameter
    folder_id = request.query_params.get("folder_id")
    if not folder_id:
        return JSONResponse(
            {"error": "folder_id query parameter is required"}, status_code=400
        )

    # Get user's UiPath credentials
    user_data = await db.get_user_by_id(user.id)
    if not user_data.get("uipath_url"):
        return JSONResponse(
            {"error": "UiPath configuration not set. Please configure in Settings."},
            status_code=400,
        )

    # Proactively ensure valid token (OAuth only, PAT passes through)
    valid_token = await _ensure_valid_oauth_token(user.id)
    if not valid_token:
        return JSONResponse(
            {"error": "UiPath access token not configured. Please configure in Settings."},
            status_code=400,
        )

    try:
        from .uipath_client import UiPathClient

        client = UiPathClient()
        processes = await client.list_processes(
            folder_id=folder_id,
            uipath_url=user_data["uipath_url"],
            uipath_access_token=valid_token,
        )

        return JSONResponse({"count": len(processes), "processes": processes})

    except Exception as e:
        error_msg = str(e)

        # Try to refresh token if 401 error
        new_token = await _refresh_oauth_token_if_needed(user.id, error_msg)

        if new_token:
            # Retry with new token
            try:
                processes = await client.list_processes(
                    folder_id=folder_id,
                    uipath_url=user_data["uipath_url"],
                    uipath_access_token=new_token,
                )
                return JSONResponse({"count": len(processes), "processes": processes})
            except Exception as retry_error:
                return JSONResponse({"error": str(retry_error)}, status_code=500)

        return JSONResponse({"error": error_msg}, status_code=500)


# ==================== MCP Endpoints ====================


async def sse_handler(request):
    """Handle SSE connections for MCP protocol.

    URL format: /mcp/{tenant_name}/{server_name}/sse
    Method: GET

    Authentication methods (in order of precedence):
    1. Server API token: Generated per-server token for external clients
    2. JWT token: User authentication token

    Token can be provided via:
    - Authorization header: "Bearer <token>"
    - Query parameter: ?token=<token>
    """
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]
    logger.info(
        "[SSE] Incoming connection: path=%s method=%s query=%s",
        request.url.path,
        request.method,
        str(request.url.query),
    )
    try:
        masked_headers = _mask_authorization(dict(request.headers))
        logger.debug("[SSE] Headers: %s", masked_headers)
    except Exception:
        pass

    # Check authentication
    if not await check_mcp_access(request, db, tenant_name, server_name):
        logger.warning(f"SSE access denied: {tenant_name}/{server_name}")
        return JSONResponse(
            {
                "error": "Access denied. Please provide a valid authentication token.",
                "details": "Use either a server API token or your user JWT token via Authorization header or ?token= query parameter.",
            },
            status_code=403,
        )

    logger.debug("[SSE] Getting/creating MCP server: %s/%s", tenant_name, server_name)
    mcp_server_instance = await get_or_create_mcp_server(tenant_name, server_name)
    logger.debug(
        "[SSE] MCP server ready: %s/%s -> %s",
        tenant_name,
        server_name,
        bool(mcp_server_instance),
    )

    if not mcp_server_instance:
        logger.error(f"MCP server not found: {tenant_name}/{server_name}")
        return JSONResponse(
            {"error": f"MCP server not found: {tenant_name}/{server_name}"},
            status_code=404,
        )

    mcp_server = mcp_server_instance.get_server()

    # SSE (Server-Sent Events) protocol
    key = f"{tenant_name}/{server_name}"
    if key not in sse_transports:
        logger.info(f"[SSE] Creating new SSE transport for {key}")
        sse_transports[key] = SseServerTransport(
            f"/mcp/{tenant_name}/{server_name}/sse/messages"
        )

    sse = sse_transports[key]

    logger.info(f"[SSE] Starting SSE session for {key}")
    # Handle the SSE connection directly
    try:
        async with sse.connect_sse(request.scope, request.receive, request._send) as (
            read_stream,
            write_stream,
        ):
            logger.debug("[SSE] connect_sse opened for %s", key)
            # Mark init started for this key to allow message POST handler to wait briefly
            evt = sse_init_started.get(key)
            if not evt:
                evt = asyncio.Event()
                sse_init_started[key] = evt
            evt.set()
            # Run the MCP server session
            logger.debug("[SSE] Running MCP server session (run) for %s", key)
            await mcp_server.run(
                read_stream, write_stream, mcp_server.create_initialization_options()
            )
        logger.info(f"[SSE] Session ended for {key}")
        # SSE 연결이 정상적으로 종료됨 - 빈 응답 반환
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"[SSE] Error in session {key}: {e}", exc_info=True)
        return JSONResponse(
            {"error": f"SSE session error: {str(e)}"}, 
            status_code=500
        )


async def http_streamable_post_handler(request):
    """Handle HTTP Streamable POST requests for MCP protocol.

    URL format: /mcp/{tenant_name}/{server_name}
    Method: POST

    Authentication methods (in order of precedence):
    1. Server API token: Generated per-server token for external clients
    2. JWT token: User authentication token

    Token can be provided via:
    - Authorization header: "Bearer <token>"
    - Query parameter: ?token=<token>
    """
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]
    logger.info(
        "[HTTP-Streamable] Incoming: path=%s method=%s query=%s",
        request.url.path,
        request.method,
        str(request.url.query),
    )
    try:
        masked_headers = _mask_authorization(dict(request.headers))
        logger.debug("[HTTP-Streamable] Headers: %s", masked_headers)
    except Exception:
        pass

    # Check authentication
    if not await check_mcp_access(request, db, tenant_name, server_name):
        logger.warning(f"HTTP Streamable access denied: {tenant_name}/{server_name}")
        return JSONResponse(
            {
                "error": "Access denied. Please provide a valid authentication token.",
                "details": "Use either a server API token or your user JWT token via Authorization header or ?token= query parameter.",
            },
            status_code=403,
        )

    logger.debug(
        "[HTTP-Streamable] Getting/creating MCP server: %s/%s", tenant_name, server_name
    )
    mcp_server_instance = await get_or_create_mcp_server(tenant_name, server_name)
    logger.debug(
        "[HTTP-Streamable] MCP server ready: %s/%s -> %s",
        tenant_name,
        server_name,
        bool(mcp_server_instance),
    )

    if not mcp_server_instance:
        logger.error(f"MCP server not found: {tenant_name}/{server_name}")
        return JSONResponse(
            {"error": f"MCP server not found: {tenant_name}/{server_name}"},
            status_code=404,
        )

    mcp_server = mcp_server_instance.get_server()

    # HTTP Streamable protocol - handle request directly
    # Track if response was sent
    response_started = False

    async def tracking_send(message):
        nonlocal response_started
        if message["type"] == "http.response.start":
            response_started = True
        await request._send(message)

    logger.debug(f"Processing HTTP Streamable request for {tenant_name}/{server_name}")

    key = f"{tenant_name}/{server_name}"
    if key not in streamable_transports:
        logger.info(f"[HTTP-Streamable] Creating transport for {key}")
        streamable_transports[key] = StreamableHTTPServerTransport(mcp_session_id=None)

        # Establish the connection BEFORE handling the first request to avoid race
        connect_cm = streamable_transports[key].connect()
        try:
            logger.debug("[HTTP-Streamable] Opening connect().__aenter__ for %s", key)
            read_stream, write_stream = await connect_cm.__aenter__()
            logger.debug("[HTTP-Streamable] Stream established for %s", key)
        except Exception:
            logger.exception("Failed to open streamable connect()")
            return JSONResponse(
                {"error": "Failed to initialize stream"}, status_code=500
            )

        async def run_streamable_session():
            try:
                logger.debug(
                    "[HTTP-Streamable] run_streamable_session starting for %s", key
                )
                init_opts = mcp_server.create_initialization_options()
                logger.debug(
                    "[HTTP-Streamable] Initialization options for %s: %s",
                    key,
                    init_opts,
                )
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    init_opts,
                )
            except Exception:
                logger.exception("Streamable session task error")
            finally:
                try:
                    await connect_cm.__aexit__(None, None, None)
                except Exception:
                    logger.debug("Error during streamable connect() exit")
                # Cleanup on exit
                streamable_transports.pop(key, None)
                streamable_tasks.pop(key, None)

        # Mark init started
        evt = streamable_init_started.get(key)
        if not evt:
            evt = asyncio.Event()
            streamable_init_started[key] = evt
        streamable_tasks[key] = asyncio.create_task(run_streamable_session())
        evt.set()
        # Record start time and small delay to let init handshake start
        try:
            import time

            streamable_started_at[key] = time.monotonic()
        except Exception:
            pass
        await asyncio.sleep(0.1)

    streamable = streamable_transports[key]
    try:
        import time

        started = streamable_started_at.get(key)
        if started:
            logger.debug(
                "[HTTP-Streamable] Time since run task scheduled for %s: %.3fs",
                key,
                time.monotonic() - started,
            )
    except Exception:
        pass
    logger.debug("[HTTP-Streamable] Calling handle_request for %s", key)
    await streamable.handle_request(request.scope, request.receive, tracking_send)
    logger.debug(
        "[HTTP-Streamable] handle_request returned for %s; response_started=%s",
        key,
        response_started,
    )

    logger.debug(f"HTTP Streamable request completed for {tenant_name}/{server_name}")
    # Response already sent via tracking_send
    # Return a no-op ASGI callable to satisfy Starlette
    return NoOpResponse()


async def sse_message_post_handler(request):
    """Handle POST messages for SSE transport."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]

    # Check authentication (same as SSE handler)
    if not await check_mcp_access(request, db, tenant_name, server_name):
        return JSONResponse(
            {
                "error": "Access denied. Please provide a valid authentication token.",
                "details": "Use either a server API token or your user JWT token via Authorization header or ?token= query parameter.",
            },
            status_code=403,
        )

    # Get SSE transport
    key = f"{tenant_name}/{server_name}"
    if key not in sse_transports:
        return JSONResponse({"error": "No active SSE connection"}, status_code=404)

    sse = sse_transports[key]
    logger.debug("[SSE] POST message for %s", key)

    # If SSE session just started, give a brief moment for initialization handshake
    evt = sse_init_started.get(key)
    if evt and not evt.is_set():
        try:
            await asyncio.wait_for(evt.wait(), timeout=0.5)
        except Exception:
            pass
    # Even if set, allow a minimal delay to reduce race conditions
    await asyncio.sleep(0.05)

    # Handle the POST message directly (it sends response via ASGI)
    # We need to create a custom send wrapper to track if response was sent
    response_started = False

    async def tracking_send(message):
        nonlocal response_started
        if message["type"] == "http.response.start":
            response_started = True
        await request._send(message)

    await sse.handle_post_message(request.scope, request.receive, tracking_send)

    # Response already sent via tracking_send
    # Return a no-op ASGI callable to satisfy Starlette
    return NoOpResponse()


# ==================== Health Check ====================


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy"})


# ==================== MCP Server Management ====================


async def list_servers(request):
    """List MCP servers (filtered by user ownership)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Admin can see all servers, users see only their own
    if user.role == "admin":
        servers = await db.list_servers()
    else:
        servers = await db.list_servers(user_id=user.id)

    return JSONResponse({"count": len(servers), "servers": servers})


async def create_server(request):
    """Create a new MCP server endpoint."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    try:
        data = await request.json()
        server = ServerCreate(**data)

        # Check if exists
        existing = await db.get_server(server.tenant_name, server.server_name)
        if existing:
            return JSONResponse(
                {
                    "error": f"Server '{server.tenant_name}/{server.server_name}' already exists"
                },
                status_code=409,
            )

        # Create server with current user as owner
        server_id = await db.create_server(
            tenant_name=server.tenant_name,
            server_name=server.server_name,
            user_id=user.id,
            description=server.description,
        )

        created = await db.get_server(server.tenant_name, server.server_name)
        return JSONResponse(created, status_code=201)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def get_server(request):
    """Get a specific MCP server."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    server = await db.get_server(tenant_name, server_name)

    if not server:
        return JSONResponse(
            {"error": f"Server '{tenant_name}/{server_name}' not found"},
            status_code=404,
        )

    return JSONResponse(server)


async def update_server(request):
    """Update an MCP server."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    try:
        data = await request.json()
        server_update = ServerUpdate(**data)

        # Check if exists
        existing = await db.get_server(tenant_name, server_name)
        if not existing:
            return JSONResponse(
                {"error": f"Server '{tenant_name}/{server_name}' not found"},
                status_code=404,
            )

        await db.update_server(
            tenant_name=tenant_name,
            server_name=server_name,
            description=server_update.description,
        )

        updated = await db.get_server(tenant_name, server_name)
        return JSONResponse(updated)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def delete_server(request):
    """Delete an MCP server and all its tools."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    # Remove from cache
    key = f"{tenant_name}/{server_name}"
    if key in mcp_servers:
        del mcp_servers[key]

    deleted = await db.delete_server(tenant_name, server_name)

    if not deleted:
        return JSONResponse(
            {"error": f"Server '{tenant_name}/{server_name}' not found"},
            status_code=404,
        )

    return JSONResponse({"message": "Server deleted"}, status_code=204)


# ==================== MCP Server Token Management ====================


async def generate_server_token(request):
    """Generate a new API token for an MCP server."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    token = await db.generate_server_token(tenant_name, server_name)

    if not token:
        return JSONResponse(
            {"error": f"Server '{tenant_name}/{server_name}' not found"},
            status_code=404,
        )

    return JSONResponse({"token": token, "message": "API token generated successfully"})


async def get_server_token(request):
    """Get the current API token for an MCP server."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    token = await db.get_server_token(tenant_name, server_name)

    if token is None:
        return JSONResponse({"token": None, "message": "No API token generated yet"})

    return JSONResponse({"token": token})


async def revoke_server_token(request):
    """Revoke (delete) the API token for an MCP server."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    revoked = await db.revoke_server_token(tenant_name, server_name)

    if not revoked:
        return JSONResponse(
            {"error": f"Server '{tenant_name}/{server_name}' not found"},
            status_code=404,
        )

    return JSONResponse({"message": "API token revoked"})


# ==================== MCP Tool Management ====================


async def list_tools(request):
    """List all tools for a specific MCP server."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    server = await db.get_server(tenant_name, server_name)
    if not server:
        return JSONResponse(
            {"error": f"Server '{tenant_name}/{server_name}' not found"},
            status_code=404,
        )

    tools = await db.list_tools(server["id"])
    return JSONResponse({"count": len(tools), "tools": tools})


async def create_tool(request):
    """Create a new tool for an MCP server."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    try:
        server = await db.get_server(tenant_name, server_name)
        if not server:
            return JSONResponse(
                {"error": f"Server '{tenant_name}/{server_name}' not found"},
                status_code=404,
            )

        data = await request.json()
        tool = ToolCreate(**data)

        # Check if tool exists
        existing = await db.get_tool(server["id"], tool.name)
        if existing:
            return JSONResponse(
                {"error": f"Tool '{tool.name}' already exists in this server"},
                status_code=409,
            )

        # Validate tool type and required fields
        if tool.tool_type == "builtin":
            if not tool.builtin_tool_id:
                return JSONResponse(
                    {"error": "builtin_tool_id is required for builtin tool type"},
                    status_code=400,
                )
            # Verify builtin tool exists and is active
            builtin_tool = await db.get_builtin_tool(tool.builtin_tool_id)
            if not builtin_tool:
                return JSONResponse(
                    {"error": f"Built-in tool with ID {tool.builtin_tool_id} not found"},
                    status_code=404,
                )
            if not builtin_tool.get("is_active"):
                return JSONResponse(
                    {"error": f"Built-in tool '{builtin_tool['name']}' is not active"},
                    status_code=400,
                )
        elif tool.tool_type == "uipath":
            if not tool.uipath_process_key:
                return JSONResponse(
                    {"error": "uipath_process_key is required for uipath tool type"},
                    status_code=400,
                )

        # Create tool
        tool_id = await db.add_tool(
            server_id=server["id"],
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            tool_type=tool.tool_type,
            uipath_process_name=tool.uipath_process_name,
            uipath_process_key=tool.uipath_process_key,
            uipath_folder_path=tool.uipath_folder_path,
            uipath_folder_id=tool.uipath_folder_id,
            builtin_tool_id=tool.builtin_tool_id,
        )

        # Invalidate MCP server cache to reload tools
        key = f"{tenant_name}/{server_name}"
        if key in mcp_servers:
            del mcp_servers[key]

        created = await db.get_tool(server["id"], tool.name)
        return JSONResponse(created, status_code=201)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def get_tool(request):
    """Get a specific tool."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]
    tool_name = request.path_params["tool_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    server = await db.get_server(tenant_name, server_name)
    if not server:
        return JSONResponse(
            {"error": f"Server '{tenant_name}/{server_name}' not found"},
            status_code=404,
        )

    tool = await db.get_tool(server["id"], tool_name)
    if not tool:
        return JSONResponse({"error": f"Tool '{tool_name}' not found"}, status_code=404)

    return JSONResponse(tool)


async def update_tool(request):
    """Update a tool."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]
    tool_name = request.path_params["tool_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    try:
        server = await db.get_server(tenant_name, server_name)
        if not server:
            return JSONResponse(
                {"error": f"Server '{tenant_name}/{server_name}' not found"},
                status_code=404,
            )

        existing = await db.get_tool(server["id"], tool_name)
        if not existing:
            return JSONResponse(
                {"error": f"Tool '{tool_name}' not found"}, status_code=404
            )

        data = await request.json()
        tool_update = ToolUpdate(**data)

        await db.update_tool(
            server_id=server["id"],
            tool_name=tool_name,
            description=tool_update.description,
            input_schema=tool_update.input_schema,
            tool_type=tool_update.tool_type,
            uipath_process_name=tool_update.uipath_process_name,
            uipath_process_key=tool_update.uipath_process_key,
            uipath_folder_path=tool_update.uipath_folder_path,
            uipath_folder_id=tool_update.uipath_folder_id,
            builtin_tool_id=tool_update.builtin_tool_id,
        )

        # Invalidate cache
        key = f"{tenant_name}/{server_name}"
        if key in mcp_servers:
            del mcp_servers[key]

        updated = await db.get_tool(server["id"], tool_name)
        return JSONResponse(updated)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def delete_tool(request):
    """Delete a tool."""
    tenant_name = request.path_params["tenant_name"]
    server_name = request.path_params["server_name"]
    tool_name = request.path_params["tool_name"]

    # Check authentication and ownership
    if not await check_server_ownership(request, db, tenant_name, server_name):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    server = await db.get_server(tenant_name, server_name)
    if not server:
        return JSONResponse(
            {"error": f"Server '{tenant_name}/{server_name}' not found"},
            status_code=404,
        )

    deleted = await db.delete_tool(server["id"], tool_name)

    if not deleted:
        return JSONResponse({"error": f"Tool '{tool_name}' not found"}, status_code=404)

    # Invalidate cache
    key = f"{tenant_name}/{server_name}"
    if key in mcp_servers:
        del mcp_servers[key]

    return JSONResponse({"message": "Tool deleted"}, status_code=204)


# ==================== Built-in Tool Management ====================


async def list_builtin_tools(request):
    """List all built-in tools."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Get active_only parameter (default: true)
    active_only = request.query_params.get("active_only", "true").lower() == "true"

    tools = await db.list_builtin_tools(active_only=active_only)
    return JSONResponse({"count": len(tools), "tools": tools})


async def create_builtin_tool(request):
    """Create a new built-in tool."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Only admin can create built-in tools
    if user.role != "admin":
        return JSONResponse(
            {"error": "Only administrators can create built-in tools"}, status_code=403
        )

    try:
        data = await request.json()
        tool = BuiltinToolCreate(**data)

        # Check if tool exists
        existing = await db.get_builtin_tool_by_name(tool.name)
        if existing:
            return JSONResponse(
                {"error": f"Built-in tool '{tool.name}' already exists"},
                status_code=409,
            )

        # Create tool
        tool_id = await db.create_builtin_tool(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            python_function=tool.python_function,
            api_key=tool.api_key,
        )

        created = await db.get_builtin_tool(tool_id)
        return JSONResponse(created, status_code=201)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def get_builtin_tool(request):
    """Get a specific built-in tool."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    tool_id = int(request.path_params["tool_id"])
    tool = await db.get_builtin_tool(tool_id)

    if not tool:
        return JSONResponse(
            {"error": f"Built-in tool with ID {tool_id} not found"}, status_code=404
        )

    return JSONResponse(tool)


async def update_builtin_tool(request):
    """Update a built-in tool."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Only admin can update built-in tools
    if user.role != "admin":
        return JSONResponse(
            {"error": "Only administrators can update built-in tools"}, status_code=403
        )

    try:
        tool_id = int(request.path_params["tool_id"])
        existing = await db.get_builtin_tool(tool_id)
        if not existing:
            return JSONResponse(
                {"error": f"Built-in tool with ID {tool_id} not found"},
                status_code=404,
            )

        data = await request.json()
        tool_update = BuiltinToolUpdate(**data)

        await db.update_builtin_tool(
            tool_id=tool_id,
            description=tool_update.description,
            input_schema=tool_update.input_schema,
            python_function=tool_update.python_function,
            api_key=tool_update.api_key,
            is_active=tool_update.is_active,
        )

        updated = await db.get_builtin_tool(tool_id)
        return JSONResponse(updated)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def delete_builtin_tool(request):
    """Delete a built-in tool."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Only admin can delete built-in tools
    if user.role != "admin":
        return JSONResponse(
            {"error": "Only administrators can delete built-in tools"}, status_code=403
        )

    tool_id = int(request.path_params["tool_id"])
    deleted = await db.delete_builtin_tool(tool_id)

    if not deleted:
        return JSONResponse(
            {"error": f"Built-in tool with ID {tool_id} not found"}, status_code=404
        )

    return JSONResponse({"message": "Built-in tool deleted"}, status_code=204)


# ==================== User Management (Admin) ====================


async def list_users_admin(request):
    """List all users (admin only)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if user.role != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    # Get all users, pending users first
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT id, username, email, role, is_active, created_at FROM users ORDER BY is_active ASC, created_at DESC"
        )
        rows = await cursor.fetchall()
        users = [dict(row) for row in rows]

    return JSONResponse({"count": len(users), "users": users})


async def approve_user_admin(request):
    """Approve a user (admin only)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if user.role != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    try:
        user_id = int(request.path_params["user_id"])

        # Get user
        target_user = await db.get_user_by_id(user_id)
        if not target_user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        # Approve user (set is_active = 1)
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE users SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,),
            )
            await conn.commit()

        logger.info(f"User approved: {target_user['username']} (id={user_id})")

        # Get updated user
        updated_user = await db.get_user_by_id(user_id)
        user_data = {
            k: v
            for k, v in updated_user.items()
            if k not in ["hashed_password", "uipath_access_token", "uipath_client_secret"]
        }

        return JSONResponse(user_data)

    except Exception as e:
        logger.error(f"Error approving user: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


async def deactivate_user_admin(request):
    """Deactivate a user (admin only)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if user.role != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    try:
        user_id = int(request.path_params["user_id"])

        # Cannot deactivate self
        if user_id == user.id:
            return JSONResponse(
                {"error": "Cannot deactivate your own account"}, status_code=400
            )

        # Get user
        target_user = await db.get_user_by_id(user_id)
        if not target_user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        # Deactivate user (set is_active = 0)
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,),
            )
            await conn.commit()

        logger.info(f"User deactivated: {target_user['username']} (id={user_id})")

        # Get updated user
        updated_user = await db.get_user_by_id(user_id)
        user_data = {
            k: v
            for k, v in updated_user.items()
            if k not in ["hashed_password", "uipath_access_token", "uipath_client_secret"]
        }

        return JSONResponse(user_data)

    except Exception as e:
        logger.error(f"Error deactivating user: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


async def delete_user_admin(request):
    """Delete a user (admin only)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if user.role != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    try:
        user_id = int(request.path_params["user_id"])

        # Cannot delete self
        if user_id == user.id:
            return JSONResponse(
                {"error": "Cannot delete your own account"}, status_code=400
            )

        # Get user
        target_user = await db.get_user_by_id(user_id)
        if not target_user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        # Delete user
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await conn.commit()

        logger.info(f"User deleted: {target_user['username']} (id={user_id})")

        return JSONResponse({"message": "User deleted"}, status_code=204)

    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


# ==================== User Management (Admin) ====================


async def list_users_admin(request):
    """List all users (admin only)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if user.role != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    # Get all users
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            """
            SELECT id, username, email, role, is_active, created_at 
            FROM users 
            ORDER BY 
                CASE is_active 
                    WHEN 0 THEN 1 
                    WHEN 1 THEN 2 
                END,
                created_at DESC
            """
        )
        rows = await cursor.fetchall()
        users = [dict(row) for row in rows]

    return JSONResponse({"count": len(users), "users": users})


async def create_user_admin(request):
    """Create a new user (admin only)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if user.role != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    try:
        data = await request.json()
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role", "user")

        if not username or not email or not password:
            return JSONResponse(
                {"error": "Username, email, and password are required"}, status_code=400
            )

        # Check if user exists
        existing = await db.get_user_by_username(username)
        if existing:
            return JSONResponse(
                {"error": f"User '{username}' already exists"}, status_code=409
            )

        # Create user
        user_id = await db.create_user(username, email, password, role)

        # Get created user
        created_user = await db.get_user_by_id(user_id)
        user_data = {
            k: v
            for k, v in created_user.items()
            if k not in ["hashed_password", "uipath_access_token", "uipath_client_secret"]
        }

        return JSONResponse(user_data, status_code=201)

    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


async def approve_user_admin(request):
    """Approve a user (admin only)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if user.role != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    try:
        user_id = int(request.path_params["user_id"])

        # Get user
        target_user = await db.get_user_by_id(user_id)
        if not target_user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        # Approve user (set is_active = 1)
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE users SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,),
            )
            await conn.commit()

        logger.info(f"User approved: {target_user['username']} (id={user_id})")

        # Get updated user
        updated_user = await db.get_user_by_id(user_id)
        user_data = {
            k: v
            for k, v in updated_user.items()
            if k not in ["hashed_password", "uipath_access_token", "uipath_client_secret"]
        }

        return JSONResponse(user_data)

    except Exception as e:
        logger.error(f"Error approving user: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


async def deactivate_user_admin(request):
    """Deactivate a user (admin only)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if user.role != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    try:
        user_id = int(request.path_params["user_id"])

        # Cannot deactivate self
        if user_id == user.id:
            return JSONResponse(
                {"error": "Cannot deactivate your own account"}, status_code=400
            )

        # Get user
        target_user = await db.get_user_by_id(user_id)
        if not target_user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        # Deactivate user (set is_active = 0)
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,),
            )
            await conn.commit()

        logger.info(f"User deactivated: {target_user['username']} (id={user_id})")

        # Get updated user
        updated_user = await db.get_user_by_id(user_id)
        user_data = {
            k: v
            for k, v in updated_user.items()
            if k not in ["hashed_password", "uipath_access_token", "uipath_client_secret"]
        }

        return JSONResponse(user_data)

    except Exception as e:
        logger.error(f"Error deactivating user: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


async def delete_user_admin(request):
    """Delete a user (admin only)."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    if user.role != "admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    try:
        user_id = int(request.path_params["user_id"])

        # Cannot delete self
        if user_id == user.id:
            return JSONResponse(
                {"error": "Cannot delete your own account"}, status_code=400
            )

        # Get user
        target_user = await db.get_user_by_id(user_id)
        if not target_user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        # Delete user
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await conn.commit()

        return JSONResponse({"message": "User deleted"}, status_code=204)

    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


# ==================== Static Files & SPA ====================


async def serve_spa(request):
    """Serve the SPA for all non-API routes."""
    static_dir = Path(__file__).parent.parent / "static"
    index_file = static_dir / "index.html"

    if index_file.exists():
        return FileResponse(index_file)
    else:
        return JSONResponse(
            {"error": "Frontend not built. Run 'npm run build' in frontend directory."},
            status_code=404,
        )


# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        # Authentication endpoints
        Route("/auth/register", register, methods=["POST"]),
        Route("/auth/login", login, methods=["POST"]),
        Route("/auth/me", get_me, methods=["GET"]),
        Route("/auth/uipath-config", update_uipath_config, methods=["PUT"]),
        Route("/auth/change-password", change_password, methods=["PUT"]),
        Route("/api/uipath/folders", list_uipath_folders, methods=["GET"]),
        Route("/api/uipath/processes", list_uipath_processes, methods=["GET"]),
        # MCP endpoints
        Route(
            "/mcp/{tenant_name}/{server_name}",
            http_streamable_post_handler,
            methods=["GET", "POST", "DELETE"],
        ),  # HTTP Streamable
        Route(
            "/mcp/{tenant_name}/{server_name}/sse", sse_handler, methods=["GET"]
        ),  # SSE
        Route(
            "/mcp/{tenant_name}/{server_name}/sse/messages",
            sse_message_post_handler,
            methods=["POST"],
        ),  # SSE Messages
        # Health check
        Route("/health", health_check),
        # MCP Server Management API
        Route("/api/servers", list_servers, methods=["GET"]),
        Route("/api/servers", create_server, methods=["POST"]),
        Route("/api/servers/{tenant_name}/{server_name}", get_server, methods=["GET"]),
        Route(
            "/api/servers/{tenant_name}/{server_name}", update_server, methods=["PUT"]
        ),
        Route(
            "/api/servers/{tenant_name}/{server_name}",
            delete_server,
            methods=["DELETE"],
        ),
        # MCP Server Token Management API
        Route(
            "/api/servers/{tenant_name}/{server_name}/token",
            generate_server_token,
            methods=["POST"],
        ),
        Route(
            "/api/servers/{tenant_name}/{server_name}/token",
            get_server_token,
            methods=["GET"],
        ),
        Route(
            "/api/servers/{tenant_name}/{server_name}/token",
            revoke_server_token,
            methods=["DELETE"],
        ),
        # MCP Tool Management API
        Route(
            "/api/servers/{tenant_name}/{server_name}/tools",
            list_tools,
            methods=["GET"],
        ),
        Route(
            "/api/servers/{tenant_name}/{server_name}/tools",
            create_tool,
            methods=["POST"],
        ),
        Route(
            "/api/servers/{tenant_name}/{server_name}/tools/{tool_name}",
            get_tool,
            methods=["GET"],
        ),
        Route(
            "/api/servers/{tenant_name}/{server_name}/tools/{tool_name}",
            update_tool,
            methods=["PUT"],
        ),
        Route(
            "/api/servers/{tenant_name}/{server_name}/tools/{tool_name}",
            delete_tool,
            methods=["DELETE"],
        ),
        # Built-in Tool Management API
        Route("/api/builtin-tools", list_builtin_tools, methods=["GET"]),
        Route("/api/builtin-tools", create_builtin_tool, methods=["POST"]),
        Route("/api/builtin-tools/{tool_id}", get_builtin_tool, methods=["GET"]),
        Route("/api/builtin-tools/{tool_id}", update_builtin_tool, methods=["PUT"]),
        Route(
            "/api/builtin-tools/{tool_id}", delete_builtin_tool, methods=["DELETE"]
        ),
        # User Management API (Admin)
        Route("/api/admin/users", list_users_admin, methods=["GET"]),
        Route("/api/admin/users/{user_id}/approve", approve_user_admin, methods=["POST"]),
        Route("/api/admin/users/{user_id}/deactivate", deactivate_user_admin, methods=["POST"]),
        Route("/api/admin/users/{user_id}", delete_user_admin, methods=["DELETE"]),
    ],
    on_startup=[startup],
)

# Check if static directory exists and mount static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    # Mount static assets (JS, CSS, images, etc.)
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Add SPA fallback route for all other paths
    # This must be added after mounting the app
    app.add_route("/{path:path}", serve_spa, methods=["GET"])

# Store db in app state
app.state.db = db

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
