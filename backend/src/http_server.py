"""HTTP Streamable (SSE) server for MCP with authentication."""

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response
from starlette.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http import StreamableHTTPServerTransport
import json
from datetime import timedelta

from .mcp_server import DynamicMCPServer
from .database import Database
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
    await db.initialize()


async def get_or_create_mcp_server(
    tenant_name: str, server_name: str
) -> DynamicMCPServer:
    """Get or create MCP server instance for endpoint."""
    key = f"{tenant_name}/{server_name}"

    if key not in mcp_servers:
        server_data = await db.get_server(tenant_name, server_name)
        if not server_data:
            return None

        # Pass user_id to MCP server for UiPath credentials
        mcp_server = DynamicMCPServer(
            server_data["id"], db, user_id=server_data["user_id"]
        )
        await mcp_server.initialize()
        mcp_servers[key] = mcp_server

    return mcp_servers[key]


# ==================== Authentication Endpoints ====================


async def register(request):
    """Register a new user."""
    try:
        data = await request.json()
        user_data = UserCreate(**data)

        # Check if username exists
        existing = await db.get_user_by_username(user_data.username)
        if existing:
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
        user_response = UserResponse(
            **{k: v for k, v in user.items() if k != "hashed_password"}
        )

        return JSONResponse(user_response.model_dump(), status_code=201)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def login(request):
    """Login and get access token."""
    try:
        data = await request.json()
        login_data = UserLogin(**data)

        # Get user
        user = await db.get_user_by_username(login_data.username)
        if not user:
            return JSONResponse(
                {"error": "Invalid username or password"}, status_code=401
            )

        # Verify password
        if not db.verify_password(login_data.password, user["hashed_password"]):
            return JSONResponse(
                {"error": "Invalid username or password"}, status_code=401
            )

        # Check if active
        if not user["is_active"]:
            return JSONResponse({"error": "User account is inactive"}, status_code=403)

        # Create access token
        access_token = create_access_token(
            data={"sub": user["username"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        user_response = UserResponse(
            **{k: v for k, v in user.items() if k != "hashed_password"}
        )

        token_response = Token(access_token=access_token, user=user_response)

        return JSONResponse(token_response.model_dump())

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def get_me(request):
    """Get current user info."""
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # Exclude sensitive data
    user_data = {
        k: v
        for k, v in user.model_dump().items()
        if k not in ["hashed_password", "uipath_access_token"]
    }
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
            uipath_folder_path=config.uipath_folder_path,
        )

        # Get updated user
        updated_user = await db.get_user_by_id(user.id)
        user_data = {
            k: v
            for k, v in updated_user.items()
            if k not in ["hashed_password", "uipath_access_token"]
        }
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

    # Check authentication
    if not await check_mcp_access(request, db, tenant_name, server_name):
        return JSONResponse(
            {
                "error": "Access denied. Please provide a valid authentication token.",
                "details": "Use either a server API token or your user JWT token via Authorization header or ?token= query parameter.",
            },
            status_code=403,
        )

    mcp_server_instance = await get_or_create_mcp_server(tenant_name, server_name)

    if not mcp_server_instance:
        return JSONResponse(
            {"error": f"MCP server not found: {tenant_name}/{server_name}"},
            status_code=404,
        )

    mcp_server = mcp_server_instance.get_server()

    # SSE (Server-Sent Events) protocol
    key = f"{tenant_name}/{server_name}"
    if key not in sse_transports:
        sse_transports[key] = SseServerTransport(
            f"/mcp/{tenant_name}/{server_name}/sse/messages"
        )

    sse = sse_transports[key]

    # Handle the SSE connection directly
    async with sse.connect_sse(request.scope, request.receive, request._send) as (
        read_stream,
        write_stream,
    ):
        # Run the MCP server session
        await mcp_server.run(
            read_stream, write_stream, mcp_server.create_initialization_options()
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

    # Check authentication
    if not await check_mcp_access(request, db, tenant_name, server_name):
        return JSONResponse(
            {
                "error": "Access denied. Please provide a valid authentication token.",
                "details": "Use either a server API token or your user JWT token via Authorization header or ?token= query parameter.",
            },
            status_code=403,
        )

    mcp_server_instance = await get_or_create_mcp_server(tenant_name, server_name)

    if not mcp_server_instance:
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

    streamable = StreamableHTTPServerTransport(mcp_session_id=None)
    await streamable.handle_request(
        request.scope, request.receive, tracking_send, mcp_server
    )

    # If response was already sent by handle_request, don't send another one
    # Return None to indicate no further response needed
    if response_started:
        return None

    # If for some reason response wasn't sent, return empty response
    return Response(status_code=200)


async def sse_message_handler(request):
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

    # If response was already sent by handle_post_message, don't send another one
    # Return None to indicate no further response needed
    if response_started:
        return None

    # If for some reason response wasn't sent, return empty response
    return Response(status_code=200)


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
            sse_message_handler,
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
