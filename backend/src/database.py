"""Database module for managing MCP server endpoints, tools, and users."""

import aiosqlite
import json
import hashlib
from typing import List, Optional, Dict, Any


class Database:
    """SQLite database manager for MCP servers, tools, and users."""

    def __init__(self, db_path: str = "backend/database/mcp_servers.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    async def initialize(self):
        """Create database tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    uipath_url TEXT,
                    uipath_access_token TEXT,
                    uipath_folder_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # MCP Server endpoints table (with user ownership)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mcp_servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_name TEXT NOT NULL,
                    server_name TEXT NOT NULL,
                    description TEXT,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(tenant_name, server_name)
                )
            """)
            
            # MCP Tools table (following MCP Tool specification)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mcp_tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    input_schema TEXT NOT NULL,
                    uipath_process_name TEXT,
                    uipath_folder_path TEXT,
                    uipath_folder_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE,
                    UNIQUE(server_id, name)
                )
            """)
            
            # Create indexes for better query performance
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_mcp_servers_user 
                ON mcp_servers(user_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_mcp_servers_tenant_server 
                ON mcp_servers(tenant_name, server_name)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_mcp_tools_server 
                ON mcp_tools(server_id)
            """)
            
            await db.commit()

    # ==================== User Management ====================
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str = "user"
    ) -> int:
        """Create a new user.
        
        Args:
            username: Username
            email: Email address
            password: Plain text password (will be hashed)
            role: User role ('user' or 'admin')
            
        Returns:
            User ID
        """
        hashed_password = self._hash_password(password)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO users (username, email, hashed_password, role)
                VALUES (?, ?, ?, ?)
                """,
                (username, email, hashed_password, role)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "hashed_password": row["hashed_password"],
                    "role": row["role"],
                    "is_active": bool(row["is_active"]),
                    "uipath_url": row["uipath_url"],
                    "uipath_access_token": row["uipath_access_token"],
                    "uipath_folder_path": row["uipath_folder_path"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "hashed_password": row["hashed_password"],
                    "role": row["role"],
                    "is_active": bool(row["is_active"]),
                    "uipath_url": row["uipath_url"],
                    "uipath_access_token": row["uipath_access_token"],
                    "uipath_folder_path": row["uipath_folder_path"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return None

    async def update_user_uipath_config(
        self,
        user_id: int,
        uipath_url: Optional[str] = None,
        uipath_access_token: Optional[str] = None,
        uipath_folder_path: Optional[str] = None
    ) -> bool:
        """Update user's UiPath configuration.
        
        Args:
            user_id: User ID
            uipath_url: UiPath Cloud URL
            uipath_access_token: UiPath Personal Access Token
            uipath_folder_path: UiPath folder path
            
        Returns:
            True if updated, False if not found
        """
        updates = []
        params = []
        
        if uipath_url is not None:
            updates.append("uipath_url = ?")
            params.append(uipath_url)
        if uipath_access_token is not None:
            updates.append("uipath_access_token = ?")
            params.append(uipath_access_token)
        if uipath_folder_path is not None:
            updates.append("uipath_folder_path = ?")
            params.append(uipath_folder_path)
        
        if not updates:
            return False
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()
            return cursor.rowcount > 0

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches
        """
        return self._hash_password(plain_password) == hashed_password

    # ==================== MCP Server Management ====================
    
    async def create_server(
        self,
        tenant_name: str,
        server_name: str,
        user_id: int,
        description: Optional[str] = None
    ) -> int:
        """Create a new MCP server endpoint.
        
        Args:
            tenant_name: Tenant name for the endpoint
            server_name: Server name for the endpoint
            user_id: ID of the user creating the server
            description: Server description
            
        Returns:
            Server ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO mcp_servers (tenant_name, server_name, user_id, description)
                VALUES (?, ?, ?, ?)
                """,
                (tenant_name, server_name, user_id, description)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_server(
        self,
        tenant_name: str,
        server_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get MCP server by tenant and server name.
        
        Args:
            tenant_name: Tenant name
            server_name: Server name
            
        Returns:
            Server data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM mcp_servers WHERE tenant_name = ? AND server_name = ?",
                (tenant_name, server_name)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "tenant_name": row["tenant_name"],
                    "server_name": row["server_name"],
                    "description": row["description"],
                    "user_id": row["user_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return None

    async def get_server_by_id(self, server_id: int) -> Optional[Dict[str, Any]]:
        """Get MCP server by ID.
        
        Args:
            server_id: Server ID
            
        Returns:
            Server data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM mcp_servers WHERE id = ?",
                (server_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "tenant_name": row["tenant_name"],
                    "server_name": row["server_name"],
                    "description": row["description"],
                    "user_id": row["user_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return None

    async def list_servers(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List MCP servers.
        
        Args:
            user_id: If provided, only return servers owned by this user
            
        Returns:
            List of server data
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if user_id is not None:
                cursor = await db.execute(
                    "SELECT * FROM mcp_servers WHERE user_id = ? ORDER BY tenant_name, server_name",
                    (user_id,)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM mcp_servers ORDER BY tenant_name, server_name"
                )
            
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "tenant_name": row["tenant_name"],
                    "server_name": row["server_name"],
                    "description": row["description"],
                    "user_id": row["user_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
                for row in rows
            ]

    async def update_server(
        self,
        tenant_name: str,
        server_name: str,
        description: Optional[str] = None
    ) -> bool:
        """Update an MCP server.
        
        Args:
            tenant_name: Tenant name
            server_name: Server name
            description: New description
            
        Returns:
            True if updated, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE mcp_servers 
                SET description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE tenant_name = ? AND server_name = ?
                """,
                (description, tenant_name, server_name)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_server(
        self,
        tenant_name: str,
        server_name: str
    ) -> bool:
        """Delete an MCP server and all its tools.
        
        Args:
            tenant_name: Tenant name
            server_name: Server name
            
        Returns:
            True if deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM mcp_servers WHERE tenant_name = ? AND server_name = ?",
                (tenant_name, server_name)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def generate_server_token(
        self,
        tenant_name: str,
        server_name: str
    ) -> Optional[str]:
        """Generate a new API token for an MCP server.
        
        Args:
            tenant_name: Tenant name
            server_name: Server name
            
        Returns:
            Generated token or None if server not found
        """
        import secrets
        
        # Generate a secure random token
        token = secrets.token_urlsafe(32)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE mcp_servers 
                SET api_token = ?, updated_at = CURRENT_TIMESTAMP
                WHERE tenant_name = ? AND server_name = ?
                """,
                (token, tenant_name, server_name)
            )
            await db.commit()
            
            if cursor.rowcount > 0:
                return token
            return None

    async def get_server_token(
        self,
        tenant_name: str,
        server_name: str
    ) -> Optional[str]:
        """Get the API token for an MCP server.
        
        Args:
            tenant_name: Tenant name
            server_name: Server name
            
        Returns:
            API token or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT api_token FROM mcp_servers WHERE tenant_name = ? AND server_name = ?",
                (tenant_name, server_name)
            )
            row = await cursor.fetchone()
            
            if row:
                return row["api_token"]
            return None

    async def revoke_server_token(
        self,
        tenant_name: str,
        server_name: str
    ) -> bool:
        """Revoke (delete) the API token for an MCP server.
        
        Args:
            tenant_name: Tenant name
            server_name: Server name
            
        Returns:
            True if revoked, False if server not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE mcp_servers 
                SET api_token = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE tenant_name = ? AND server_name = ?
                """,
                (tenant_name, server_name)
            )
            await db.commit()
            return cursor.rowcount > 0

    # ==================== MCP Tool Management ====================
    
    async def add_tool(
        self,
        server_id: int,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        uipath_process_name: Optional[str] = None,
        uipath_folder_path: Optional[str] = None,
        uipath_folder_id: Optional[str] = None
    ) -> int:
        """Add a new tool to an MCP server.
        
        Args:
            server_id: Server ID
            name: Tool name (must be unique within server)
            description: Tool description
            input_schema: JSON Schema for tool input (MCP Tool spec)
            uipath_process_name: UiPath process name (optional)
            uipath_folder_path: UiPath folder path (optional)
            uipath_folder_id: UiPath folder ID (optional)
            
        Returns:
            Tool ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO mcp_tools 
                (server_id, name, description, input_schema, 
                 uipath_process_name, uipath_folder_path, uipath_folder_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    server_id,
                    name,
                    description,
                    json.dumps(input_schema),
                    uipath_process_name,
                    uipath_folder_path,
                    uipath_folder_id
                )
            )
            await db.commit()
            return cursor.lastrowid

    async def get_tool(
        self,
        server_id: int,
        tool_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get a tool by server ID and tool name.
        
        Args:
            server_id: Server ID
            tool_name: Tool name
            
        Returns:
            Tool data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM mcp_tools WHERE server_id = ? AND name = ?",
                (server_id, tool_name)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "server_id": row["server_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "input_schema": json.loads(row["input_schema"]),
                    "uipath_process_name": row["uipath_process_name"],
                    "uipath_folder_path": row["uipath_folder_path"],
                    "uipath_folder_id": row["uipath_folder_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return None

    async def list_tools(self, server_id: int) -> List[Dict[str, Any]]:
        """List all tools for a specific MCP server.
        
        Args:
            server_id: Server ID
            
        Returns:
            List of tool data
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM mcp_tools WHERE server_id = ? ORDER BY name",
                (server_id,)
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "server_id": row["server_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "input_schema": json.loads(row["input_schema"]),
                    "uipath_process_name": row["uipath_process_name"],
                    "uipath_folder_path": row["uipath_folder_path"],
                    "uipath_folder_id": row["uipath_folder_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
                for row in rows
            ]

    async def update_tool(
        self,
        server_id: int,
        tool_name: str,
        description: Optional[str] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        uipath_process_name: Optional[str] = None,
        uipath_folder_path: Optional[str] = None,
        uipath_folder_id: Optional[str] = None
    ) -> bool:
        """Update a tool.
        
        Args:
            server_id: Server ID
            tool_name: Tool name
            description: New description (optional)
            input_schema: New input schema (optional)
            uipath_process_name: New UiPath process name (optional)
            uipath_folder_path: New UiPath folder path (optional)
            uipath_folder_id: New UiPath folder ID (optional)
            
        Returns:
            True if updated, False if not found
        """
        updates = []
        params = []
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if input_schema is not None:
            updates.append("input_schema = ?")
            params.append(json.dumps(input_schema))
        if uipath_process_name is not None:
            updates.append("uipath_process_name = ?")
            params.append(uipath_process_name)
        if uipath_folder_path is not None:
            updates.append("uipath_folder_path = ?")
            params.append(uipath_folder_path)
        if uipath_folder_id is not None:
            updates.append("uipath_folder_id = ?")
            params.append(uipath_folder_id)
        
        if not updates:
            return False
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([server_id, tool_name])
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE mcp_tools SET {', '.join(updates)} WHERE server_id = ? AND name = ?",
                params
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_tool(
        self,
        server_id: int,
        tool_name: str
    ) -> bool:
        """Delete a tool.
        
        Args:
            server_id: Server ID
            tool_name: Tool name
            
        Returns:
            True if deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM mcp_tools WHERE server_id = ? AND name = ?",
                (server_id, tool_name)
            )
            await db.commit()
            return cursor.rowcount > 0
