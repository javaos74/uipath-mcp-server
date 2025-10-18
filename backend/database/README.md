# Database Directory

This directory contains the SQLite database file for the MCP server.

## Database File

- **Location**: `backend/database/mcp_servers.db`
- **Type**: SQLite 3
- **Purpose**: Stores users, MCP servers, tools, and API tokens

## Schema

The database contains the following tables:

### users
- User accounts with authentication
- UiPath configuration (URL, access token, folder path)
- Roles: `user` or `admin`

### mcp_servers
- MCP server endpoints
- Format: `/mcp/{tenant_name}/{server_name}`
- Each server has an optional API token for external clients

### mcp_tools
- Tools registered for each MCP server
- Follows MCP Tool specification
- Can be linked to UiPath processes

## Environment Variable

You can override the database path using the `DB_PATH` environment variable:

```bash
export DB_PATH=/path/to/your/database.db
```

Default: `backend/database/mcp_servers.db`

## Backup

To backup the database:

```bash
cp backend/database/mcp_servers.db backend/database/mcp_servers.db.backup
```

Or use SQLite's backup command:

```bash
sqlite3 backend/database/mcp_servers.db ".backup backend/database/mcp_servers.db.backup"
```

## Migrations

Database migrations are located in `backend/migrations/`.

To run a migration:

```bash
python backend/migrations/migration_name.py
```

## Initialization

The database is automatically initialized on first startup. Tables are created if they don't exist.

## Security

- The database file is excluded from Git (via `.gitignore`)
- API tokens are stored in plain text (consider encryption for production)
- User passwords are hashed using bcrypt

## Troubleshooting

### Database locked error

If you get a "database is locked" error:

1. Close all connections to the database
2. Check for stale lock files
3. Restart the server

### Corrupted database

If the database is corrupted:

1. Restore from backup
2. Or delete and reinitialize (will lose all data)

```bash
rm backend/database/mcp_servers.db
# Restart server to reinitialize
```
