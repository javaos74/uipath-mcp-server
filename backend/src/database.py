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
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    uipath_url TEXT,
                    uipath_auth_type TEXT DEFAULT 'pat',
                    uipath_access_token TEXT,
                    uipath_client_id TEXT,
                    uipath_client_secret TEXT,
                    uipath_folder_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Add OAuth columns if they don't exist (migration)
            try:
                await db.execute("ALTER TABLE users ADD COLUMN uipath_client_id TEXT")
                await db.commit()
            except aiosqlite.OperationalError:
                pass

            try:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN uipath_client_secret TEXT"
                )
                await db.commit()
            except aiosqlite.OperationalError:
                pass

            try:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN uipath_auth_type TEXT DEFAULT 'pat'"
                )
                await db.commit()
            except aiosqlite.OperationalError:
                pass

            # MCP Server endpoints table (with user ownership)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS mcp_servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_name TEXT NOT NULL,
                    server_name TEXT NOT NULL,
                    description TEXT,
                    user_id INTEGER NOT NULL,
                    api_token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(tenant_name, server_name)
                )
            """
            )



            # MCP Tools table (following MCP Tool specification)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS mcp_tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    input_schema TEXT NOT NULL,
                    tool_type TEXT DEFAULT 'uipath',
                    uipath_process_name TEXT,
                    uipath_process_key TEXT,
                    uipath_folder_path TEXT,
                    uipath_folder_id TEXT,
                    builtin_tool_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE,
                    FOREIGN KEY (builtin_tool_id) REFERENCES builtin_tools(id) ON DELETE SET NULL,
                    UNIQUE(server_id, name)
                )
            """
            )

            # Built-in Tools table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS builtin_tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    input_schema TEXT NOT NULL,
                    python_function TEXT NOT NULL,
                    api_key TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Add uipath_process_key column if it doesn't exist (migration)
            try:
                await db.execute(
                    "ALTER TABLE mcp_tools ADD COLUMN uipath_process_key TEXT"
                )
                await db.commit()
            except aiosqlite.OperationalError:
                # Column already exists, ignore
                pass

            # Add tool_type column if it doesn't exist (migration)
            try:
                await db.execute(
                    "ALTER TABLE mcp_tools ADD COLUMN tool_type TEXT DEFAULT 'uipath'"
                )
                await db.commit()
            except aiosqlite.OperationalError:
                pass

            # Add builtin_tool_id column if it doesn't exist (migration)
            try:
                await db.execute(
                    "ALTER TABLE mcp_tools ADD COLUMN builtin_tool_id INTEGER"
                )
                await db.commit()
            except aiosqlite.OperationalError:
                pass

            # Add api_key column to builtin_tools if it doesn't exist (migration)
            try:
                await db.execute(
                    "ALTER TABLE builtin_tools ADD COLUMN api_key TEXT"
                )
                await db.commit()
            except aiosqlite.OperationalError:
                pass

            # Migrate existing data: set tool_type to 'uipath' for NULL values
            try:
                await db.execute(
                    """
                    UPDATE mcp_tools 
                    SET tool_type = 'uipath' 
                    WHERE tool_type IS NULL
                    """
                )
                await db.commit()
                # Log migration result
                import logging
                logger = logging.getLogger(__name__)
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM mcp_tools WHERE tool_type = 'uipath'"
                )
                count = await cursor.fetchone()
                if count and count[0] > 0:
                    logger.info(f"Migrated {count[0]} existing tools to tool_type='uipath'")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Migration warning: {e}")

            # Create indexes for better query performance
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mcp_servers_user 
                ON mcp_servers(user_id)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mcp_servers_tenant_server 
                ON mcp_servers(tenant_name, server_name)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mcp_tools_server 
                ON mcp_tools(server_id)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_builtin_tools_name 
                ON builtin_tools(name)
            """
            )

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
        self, username: str, email: str, password: str, role: str = "user"
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
                (username, email, hashed_password, role),
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
                "SELECT * FROM users WHERE username = ?", (username,)
            )
            row = await cursor.fetchone()
            if row:
                # Convert sqlite Row to a plain dict for safe .get access
                row_dict = dict(row)
                return {
                    "id": row_dict.get("id"),
                    "username": row_dict.get("username"),
                    "email": row_dict.get("email"),
                    "hashed_password": row_dict.get("hashed_password"),
                    "role": row_dict.get("role"),
                    "is_active": bool(row_dict.get("is_active")),
                    "uipath_url": row_dict.get("uipath_url"),
                    "uipath_auth_type": row_dict.get("uipath_auth_type", "pat"),
                    "uipath_access_token": row_dict.get("uipath_access_token"),
                    "uipath_client_id": row_dict.get("uipath_client_id"),
                    "uipath_client_secret": row_dict.get("uipath_client_secret"),
                    "uipath_folder_path": row_dict.get("uipath_folder_path"),
                    "created_at": row_dict.get("created_at"),
                    "updated_at": row_dict.get("updated_at"),
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
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                row_dict = dict(row)
                return {
                    "id": row_dict.get("id"),
                    "username": row_dict.get("username"),
                    "email": row_dict.get("email"),
                    "hashed_password": row_dict.get("hashed_password"),
                    "role": row_dict.get("role"),
                    "is_active": bool(row_dict.get("is_active")),
                    "uipath_url": row_dict.get("uipath_url"),
                    "uipath_auth_type": row_dict.get("uipath_auth_type", "pat"),
                    "uipath_access_token": row_dict.get("uipath_access_token"),
                    "uipath_client_id": row_dict.get("uipath_client_id"),
                    "uipath_client_secret": row_dict.get("uipath_client_secret"),
                    "uipath_folder_path": row_dict.get("uipath_folder_path"),
                    "created_at": row_dict.get("created_at"),
                    "updated_at": row_dict.get("updated_at"),
                }
            return None

    async def update_user_uipath_config(
        self,
        user_id: int,
        uipath_url: Optional[str] = None,
        uipath_auth_type: Optional[str] = None,
        uipath_access_token: Optional[str] = None,
        uipath_client_id: Optional[str] = None,
        uipath_client_secret: Optional[str] = None,
    ) -> bool:
        """Update user's UiPath configuration.

        Args:
            user_id: User ID
            uipath_url: UiPath Cloud URL
            uipath_auth_type: Authentication type ('pat' or 'oauth')
            uipath_access_token: UiPath Personal Access Token
            uipath_client_id: OAuth Client ID
            uipath_client_secret: OAuth Client Secret

        Returns:
            True if updated, False if not found
        """
        updates = []
        params = []

        if uipath_url is not None:
            updates.append("uipath_url = ?")
            params.append(uipath_url if uipath_url else None)
        if uipath_auth_type is not None:
            updates.append("uipath_auth_type = ?")
            params.append(uipath_auth_type)
        if uipath_access_token is not None:
            # Empty string means clear the token
            updates.append("uipath_access_token = ?")
            params.append(uipath_access_token if uipath_access_token else None)
        if uipath_client_id is not None:
            # Empty string means clear the client ID
            updates.append("uipath_client_id = ?")
            params.append(uipath_client_id if uipath_client_id else None)
        if uipath_client_secret is not None:
            # Empty string means clear the client secret
            updates.append("uipath_client_secret = ?")
            params.append(uipath_client_secret if uipath_client_secret else None)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)

        # Log the SQL query for debugging
        import logging

        logger = logging.getLogger(__name__)
        sql_query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        logger.info(f"Executing SQL: {sql_query}")
        logger.info(f"With params: {params}")

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(sql_query, params)
            await db.commit()
            logger.info(f"Updated {cursor.rowcount} rows")
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
        description: Optional[str] = None,
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
                (tenant_name, server_name, user_id, description),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_server(
        self, tenant_name: str, server_name: str
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
                (tenant_name, server_name),
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
                    "updated_at": row["updated_at"],
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
                "SELECT * FROM mcp_servers WHERE id = ?", (server_id,)
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
                    "updated_at": row["updated_at"],
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
                    (user_id,),
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
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    async def update_server(
        self, tenant_name: str, server_name: str, description: Optional[str] = None
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
                (description, tenant_name, server_name),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_server(self, tenant_name: str, server_name: str) -> bool:
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
                (tenant_name, server_name),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def generate_server_token(
        self, tenant_name: str, server_name: str
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
                (token, tenant_name, server_name),
            )
            await db.commit()

            if cursor.rowcount > 0:
                return token
            return None

    async def get_server_token(
        self, tenant_name: str, server_name: str
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
                (tenant_name, server_name),
            )
            row = await cursor.fetchone()

            if row:
                return row["api_token"]
            return None

    async def revoke_server_token(self, tenant_name: str, server_name: str) -> bool:
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
                (tenant_name, server_name),
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
        tool_type: str = "uipath",
        uipath_process_name: Optional[str] = None,
        uipath_process_key: Optional[str] = None,
        uipath_folder_path: Optional[str] = None,
        uipath_folder_id: Optional[str] = None,
        builtin_tool_id: Optional[int] = None,
    ) -> int:
        """Add a new tool to an MCP server.

        Args:
            server_id: Server ID
            name: Tool name (must be unique within server)
            description: Tool description
            input_schema: JSON Schema for tool input (MCP Tool spec)
            tool_type: Tool type ('uipath' or 'builtin')
            uipath_process_name: UiPath process name (optional)
            uipath_process_key: UiPath process key (optional)
            uipath_folder_path: UiPath folder path (optional)
            uipath_folder_id: UiPath folder ID (optional)
            builtin_tool_id: Built-in tool ID (optional)

        Returns:
            Tool ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO mcp_tools 
                (server_id, name, description, input_schema, tool_type,
                 uipath_process_name, uipath_process_key, uipath_folder_path, uipath_folder_id,
                 builtin_tool_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    server_id,
                    name,
                    description,
                    json.dumps(input_schema),
                    tool_type,
                    uipath_process_name,
                    uipath_process_key,
                    uipath_folder_path,
                    uipath_folder_id,
                    builtin_tool_id,
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_tool(
        self, server_id: int, tool_name: str
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
                (server_id, tool_name),
            )
            row = await cursor.fetchone()
            if row:
                try:
                    process_key = row["uipath_process_key"]
                except (KeyError, IndexError):
                    process_key = None
                try:
                    tool_type = row["tool_type"]
                except (KeyError, IndexError):
                    tool_type = "uipath"
                try:
                    builtin_tool_id = row["builtin_tool_id"]
                except (KeyError, IndexError):
                    builtin_tool_id = None
                return {
                    "id": row["id"],
                    "server_id": row["server_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "input_schema": json.loads(row["input_schema"]),
                    "tool_type": tool_type,
                    "uipath_process_name": row["uipath_process_name"],
                    "uipath_process_key": process_key,
                    "uipath_folder_path": row["uipath_folder_path"],
                    "uipath_folder_id": row["uipath_folder_id"],
                    "builtin_tool_id": builtin_tool_id,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
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
                (server_id,),
            )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                try:
                    process_key = row["uipath_process_key"]
                except (KeyError, IndexError):
                    process_key = None
                try:
                    tool_type = row["tool_type"]
                except (KeyError, IndexError):
                    tool_type = "uipath"
                try:
                    builtin_tool_id = row["builtin_tool_id"]
                except (KeyError, IndexError):
                    builtin_tool_id = None
                result.append(
                    {
                        "id": row["id"],
                        "server_id": row["server_id"],
                        "name": row["name"],
                        "description": row["description"],
                        "input_schema": json.loads(row["input_schema"]),
                        "tool_type": tool_type,
                        "uipath_process_name": row["uipath_process_name"],
                        "uipath_process_key": process_key,
                        "uipath_folder_path": row["uipath_folder_path"],
                        "uipath_folder_id": row["uipath_folder_id"],
                        "builtin_tool_id": builtin_tool_id,
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )
            return result

    async def update_tool(
        self,
        server_id: int,
        tool_name: str,
        description: Optional[str] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        tool_type: Optional[str] = None,
        uipath_process_name: Optional[str] = None,
        uipath_process_key: Optional[str] = None,
        uipath_folder_path: Optional[str] = None,
        uipath_folder_id: Optional[str] = None,
        builtin_tool_id: Optional[int] = None,
    ) -> bool:
        """Update a tool.

        Args:
            server_id: Server ID
            tool_name: Tool name
            description: New description (optional)
            input_schema: New input schema (optional)
            tool_type: New tool type (optional)
            uipath_process_name: New UiPath process name (optional)
            uipath_process_key: New UiPath process key (optional)
            uipath_folder_path: New UiPath folder path (optional)
            uipath_folder_id: New UiPath folder ID (optional)
            builtin_tool_id: New built-in tool ID (optional)

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
        if tool_type is not None:
            updates.append("tool_type = ?")
            params.append(tool_type)
        if uipath_process_name is not None:
            updates.append("uipath_process_name = ?")
            params.append(uipath_process_name)
        if uipath_process_key is not None:
            updates.append("uipath_process_key = ?")
            params.append(uipath_process_key)
        if uipath_folder_path is not None:
            updates.append("uipath_folder_path = ?")
            params.append(uipath_folder_path)
        if uipath_folder_id is not None:
            updates.append("uipath_folder_id = ?")
            params.append(uipath_folder_id)
        if builtin_tool_id is not None:
            updates.append("builtin_tool_id = ?")
            params.append(builtin_tool_id)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([server_id, tool_name])

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE mcp_tools SET {', '.join(updates)} WHERE server_id = ? AND name = ?",
                params,
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_tool(self, server_id: int, tool_name: str) -> bool:
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
                (server_id, tool_name),
            )
            await db.commit()
            return cursor.rowcount > 0

    # ==================== Built-in Tool Management ====================

    async def create_builtin_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        python_function: str,
        api_key: Optional[str] = None,
    ) -> int:
        """Create a new built-in tool.

        Args:
            name: Tool name (must be unique)
            description: Tool description
            input_schema: JSON Schema for tool input
            python_function: Python function name or module path
            api_key: Optional API key for external service calls

        Returns:
            Built-in tool ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO builtin_tools (name, description, input_schema, python_function, api_key)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, description, json.dumps(input_schema), python_function, api_key),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_builtin_tool(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Get a built-in tool by ID.

        Args:
            tool_id: Built-in tool ID

        Returns:
            Built-in tool data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM builtin_tools WHERE id = ?", (tool_id,)
            )
            row = await cursor.fetchone()
            if row:
                try:
                    api_key = row["api_key"]
                except (KeyError, IndexError):
                    api_key = None
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "input_schema": json.loads(row["input_schema"]),
                    "python_function": row["python_function"],
                    "api_key": api_key,
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    async def get_builtin_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a built-in tool by name.

        Args:
            name: Tool name

        Returns:
            Built-in tool data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM builtin_tools WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()
            if row:
                try:
                    api_key = row["api_key"]
                except (KeyError, IndexError):
                    api_key = None
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "input_schema": json.loads(row["input_schema"]),
                    "python_function": row["python_function"],
                    "api_key": api_key,
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    async def list_builtin_tools(
        self, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List all built-in tools.

        Args:
            active_only: If True, only return active tools

        Returns:
            List of built-in tool data
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if active_only:
                cursor = await db.execute(
                    "SELECT * FROM builtin_tools WHERE is_active = 1 ORDER BY name"
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM builtin_tools ORDER BY name"
                )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                try:
                    api_key = row["api_key"]
                except (KeyError, IndexError):
                    api_key = None
                result.append({
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "input_schema": json.loads(row["input_schema"]),
                    "python_function": row["python_function"],
                    "api_key": api_key,
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })
            return result

    async def update_builtin_tool(
        self,
        tool_id: int,
        description: Optional[str] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        python_function: Optional[str] = None,
        api_key: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Update a built-in tool.

        Args:
            tool_id: Built-in tool ID
            description: New description (optional)
            input_schema: New input schema (optional)
            python_function: New python function (optional)
            api_key: New API key (optional)
            is_active: New active status (optional)

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
        if python_function is not None:
            updates.append("python_function = ?")
            params.append(python_function)
        if api_key is not None:
            updates.append("api_key = ?")
            params.append(api_key if api_key else None)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(tool_id)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE builtin_tools SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_builtin_tool(self, tool_id: int) -> bool:
        """Delete a built-in tool.

        Args:
            tool_id: Built-in tool ID

        Returns:
            True if deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM builtin_tools WHERE id = ?", (tool_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    # ==================== Built-in Tool Management ====================

    async def create_builtin_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        python_function: str,
        api_key: Optional[str] = None,
    ) -> int:
        """Create a new built-in tool.

        Args:
            name: Tool name (must be unique)
            description: Tool description
            input_schema: JSON Schema for tool input
            python_function: Python function name or module path
            api_key: Optional API key for external service calls

        Returns:
            Built-in tool ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO builtin_tools (name, description, input_schema, python_function, api_key)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, description, json.dumps(input_schema), python_function, api_key),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_builtin_tool(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Get a built-in tool by ID.

        Args:
            tool_id: Built-in tool ID

        Returns:
            Built-in tool data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM builtin_tools WHERE id = ?", (tool_id,)
            )
            row = await cursor.fetchone()
            if row:
                try:
                    api_key = row["api_key"]
                except (KeyError, IndexError):
                    api_key = None
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "input_schema": json.loads(row["input_schema"]),
                    "python_function": row["python_function"],
                    "api_key": api_key,
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    async def get_builtin_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a built-in tool by name.

        Args:
            name: Tool name

        Returns:
            Built-in tool data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM builtin_tools WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()
            if row:
                try:
                    api_key = row["api_key"]
                except (KeyError, IndexError):
                    api_key = None
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "input_schema": json.loads(row["input_schema"]),
                    "python_function": row["python_function"],
                    "api_key": api_key,
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    async def list_builtin_tools(
        self, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List all built-in tools.

        Args:
            active_only: If True, only return active tools

        Returns:
            List of built-in tool data
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if active_only:
                cursor = await db.execute(
                    "SELECT * FROM builtin_tools WHERE is_active = 1 ORDER BY name"
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM builtin_tools ORDER BY name"
                )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                try:
                    api_key = row["api_key"]
                except (KeyError, IndexError):
                    api_key = None
                result.append({
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "input_schema": json.loads(row["input_schema"]),
                    "python_function": row["python_function"],
                    "api_key": api_key,
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })
            return result

    async def update_builtin_tool(
        self,
        tool_id: int,
        description: Optional[str] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        python_function: Optional[str] = None,
        api_key: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Update a built-in tool.

        Args:
            tool_id: Built-in tool ID
            description: New description (optional)
            input_schema: New input schema (optional)
            python_function: New python function (optional)
            api_key: New API key (optional)
            is_active: New active status (optional)

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
        if python_function is not None:
            updates.append("python_function = ?")
            params.append(python_function)
        if api_key is not None:
            updates.append("api_key = ?")
            params.append(api_key if api_key else None)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(tool_id)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE builtin_tools SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_builtin_tool(self, tool_id: int) -> bool:
        """Delete a built-in tool.

        Args:
            tool_id: Built-in tool ID

        Returns:
            True if deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM builtin_tools WHERE id = ?", (tool_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
