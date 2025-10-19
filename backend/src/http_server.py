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
from pathlib import Path
from datetime import timedelta

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
)


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
    """Register a new user."""
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

        # Create user
        user_id = await db.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role,
        )

        # Get created user
        user = await db.get_user_by_id(user_id)
        user_data = {k: v for k, v in user.items() if k != "hashed_password"}
        user_data["has_uipath_token"] = False  # New user has no token
        user_response = UserResponse(**user_data)

        logger.info(
            f"User registered successfully: {user_data.username} (id={user_id})"
        )
        return JSONResponse(user_response.model_dump(), status_code=201)

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

        # Check if active
        if not user["is_active"]:
            logger.warning(f"Login failed: inactive account - {login_data.username}")
            return JSONResponse({"error": "User account is inactive"}, status_code=403)

        # Create access token
        access_token = create_access_token(
            data={"sub": user["username"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        user_data = {k: v for k, v in user.items() if k not in ["hashed_password", "uipath_access_token"]}
        user_data["has_uipath_token"] = bool(user.get("uipath_access_token"))
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
        if k not in ["hashed_password", "uipath_access_token"]
    }
    user_data["has_uipath_token"] = bool(user.uipath_access_token)
    user_response = UserResponse(**user_data)
    return JSONResponse(user_response.model_dump())


async def update_uipath_config(request):
    """Update current user's UiPath configuration."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    try:
        data = await request.json()
        config = UiPathConfigUpdate(**data)

        # Update UiPath configuration
        await db.update_user_uipath_config(
            user_id=user.id,
            uipath_url=config.uipath_url,
            uipath_access_token=config.uipath_access_token,
        )

        # Get updated user
        updated_user = await db.get_user_by_id(user.id)
        user_data = {
            k: v
            for k, v in updated_user.items()
            if k not in ["hashed_password", "uipath_access_token"]
        }
        user_data["has_uipath_token"] = bool(updated_user.get("uipath_access_token"))
        user_response = UserResponse(**user_data)

        return JSONResponse(user_response.model_dump())

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def list_uipath_folders(request):
    """List UiPath folders using current user's credentials."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Get user's UiPath credentials
    user_data = await db.get_user_by_id(user.id)
    if not user_data.get("uipath_url") or not user_data.get("uipath_access_token"):
        return JSONResponse(
            {"error": "UiPath configuration not set. Please configure in Settings."},
            status_code=400,
        )

    try:
        from .uipath_client import UiPathClient

        client = UiPathClient()
        folders = await client.list_folders(
            uipath_url=user_data["uipath_url"],
            uipath_access_token=user_data["uipath_access_token"],
        )

        return JSONResponse({"count": len(folders), "folders": folders})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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
    if not user_data.get("uipath_url") or not user_data.get("uipath_access_token"):
        return JSONResponse(
            {"error": "UiPath configuration not set. Please configure in Settings."},
            status_code=400,
        )

    try:
        from .uipath_client import UiPathClient

        client = UiPathClient()
        processes = await client.list_processes(
            folder_id=folder_id,
            uipath_url=user_data["uipath_url"],
            uipath_access_token=user_data["uipath_access_token"],
        )

        return JSONResponse({"count": len(processes), "processes": processes})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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
    logger.info(f"SSE connection request: {tenant_name}/{server_name}")

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

    mcp_server_instance = await get_or_create_mcp_server(tenant_name, server_name)

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
        logger.info(f"Creating new SSE transport for {key}")
        sse_transports[key] = SseServerTransport(
            f"/mcp/{tenant_name}/{server_name}/sse/messages"
        )

    sse = sse_transports[key]

    logger.info(f"Starting SSE session for {key}")
    # Handle the SSE connection directly
    async with sse.connect_sse(request.scope, request.receive, request._send) as (
        read_stream,
        write_stream,
    ):
        # Run the MCP server session
        await mcp_server.run(
            read_stream, write_stream, mcp_server.create_initialization_options()
        )
    logger.info(f"SSE session ended for {key}")


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
    logger.info(f"HTTP Streamable POST request: {tenant_name}/{server_name}")

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

    mcp_server_instance = await get_or_create_mcp_server(tenant_name, server_name)

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
    streamable = StreamableHTTPServerTransport(mcp_session_id=None)
    await streamable.handle_request(
        request.scope, request.receive, tracking_send, mcp_server
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

        # Create tool
        tool_id = await db.add_tool(
            server_id=server["id"],
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            uipath_process_name=tool.uipath_process_name,
            uipath_folder_path=tool.uipath_folder_path,
            uipath_folder_id=tool.uipath_folder_id,
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
            uipath_process_name=tool_update.uipath_process_name,
            uipath_folder_path=tool_update.uipath_folder_path,
            uipath_folder_id=tool_update.uipath_folder_id,
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
            status_code=404
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
        Route("/api/uipath/folders", list_uipath_folders, methods=["GET"]),
        Route("/api/uipath/processes", list_uipath_processes, methods=["GET"]),
        # MCP endpoints
        Route(
            "/mcp/{tenant_name}/{server_name}",
            http_streamable_post_handler,
            methods=["POST"],
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
