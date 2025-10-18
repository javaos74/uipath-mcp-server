"""Authentication and authorization utilities."""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from starlette.requests import Request
from starlette.responses import JSONResponse
import os

from .database import Database
from .models import UserInDB

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token.
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request, db: Database) -> Optional[UserInDB]:
    """Get current user from JWT token.
    
    Supports token from:
    1. Authorization header: "Bearer <token>"
    2. Query parameter: ?token=<token>
    
    Args:
        request: Starlette request
        db: Database instance
        
    Returns:
        User data or None if not authenticated
    """
    token = None
    
    # Try to get token from Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
    
    # If not in header, try query parameter
    if not token:
        token = request.query_params.get("token")
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    
    user = await db.get_user_by_username(username)
    if user is None:
        return None
    
    return UserInDB(**user)


def require_auth(admin_only: bool = False):
    """Decorator to require authentication for endpoints.
    
    Args:
        admin_only: If True, require admin role
    """
    async def decorator(request: Request):
        db = request.app.state.db
        user = await get_current_user(request, db)
        
        if user is None:
            return JSONResponse(
                {"error": "Not authenticated"},
                status_code=401
            )
        
        if not user.is_active:
            return JSONResponse(
                {"error": "User account is inactive"},
                status_code=403
            )
        
        if admin_only and user.role != "admin":
            return JSONResponse(
                {"error": "Admin access required"},
                status_code=403
            )
        
        # Store user in request state
        request.state.user = user
        return None
    
    return decorator


async def check_mcp_access(
    request: Request,
    db: Database,
    tenant_name: str,
    server_name: str
) -> bool:
    """Check if request has access to MCP server.
    
    Supports two authentication methods:
    1. JWT token (user authentication)
    2. Server API token (server-specific token)
    
    Args:
        request: Starlette request
        db: Database instance
        tenant_name: Tenant name
        server_name: Server name
        
    Returns:
        True if access granted, False otherwise
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # First, try to get the server
    server = await db.get_server(tenant_name, server_name)
    if not server:
        logger.warning(f"Server not found: {tenant_name}/{server_name}")
        return False
    
    # Method 1: Check server API token
    # Get token from header or query parameter
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        logger.info(f"Token from Authorization header: {token[:20]}...")
    elif request.query_params.get("token"):
        token = request.query_params.get("token")
        logger.info(f"Token from query parameter: {token[:20]}...")
    else:
        logger.warning("No token provided in request")
    
    if token:
        # Check if it's a server API token
        server_token = await db.get_server_token(tenant_name, server_name)
        if server_token:
            logger.info(f"Server has API token: {server_token[:20]}...")
            if token == server_token:
                logger.info("✅ Valid server API token")
                return True
            else:
                logger.warning("❌ Token mismatch with server API token")
        else:
            logger.info("Server has no API token configured")
    
    # Method 2: Check JWT token (user authentication)
    user = await get_current_user(request, db)
    if not user:
        logger.warning("No valid user from JWT token")
        return False
    
    logger.info(f"User authenticated: {user.username} (role: {user.role})")
    
    # Admin can access all servers
    if user.role == "admin":
        logger.info("✅ Admin access granted")
        return True
    
    # Check if user owns the server
    if server["user_id"] == user.id:
        logger.info("✅ User owns the server")
        return True
    else:
        logger.warning(f"❌ User {user.id} does not own server (owner: {server['user_id']})")
        return False


async def check_server_ownership(
    request: Request,
    db: Database,
    tenant_name: str,
    server_name: str
) -> bool:
    """Check if current user owns the server or is admin.
    
    This is for management operations (create, update, delete).
    For MCP access, use check_mcp_access instead.
    
    Args:
        request: Starlette request
        db: Database instance
        tenant_name: Tenant name
        server_name: Server name
        
    Returns:
        True if user has access, False otherwise
    """
    user = await get_current_user(request, db)
    if not user:
        return False
    
    # Admin can access all servers
    if user.role == "admin":
        return True
    
    # Check if user owns the server
    server = await db.get_server(tenant_name, server_name)
    if not server:
        return False
    
    return server["user_id"] == user.id
