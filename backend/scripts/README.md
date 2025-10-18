# Backend Scripts

This directory contains utility scripts for testing, debugging, and managing the MCP server.

## Important: Working Directory

**All scripts in this directory must be run from the project root directory (parent of `backend/`).**

```bash
# ✅ Correct - Run from project root
cd /path/to/uipath-mcp
python backend/scripts/script_name.py

# ❌ Wrong - Don't run from backend/ or backend/scripts/
cd backend/scripts
python script_name.py  # This will fail!
```

### Why?

The scripts use relative paths like `backend/database/mcp_servers.db` and import modules from `backend/src/`. These paths only work when running from the project root.

---

## Available Scripts

### Authentication & Token Management

#### `test_mcp_authentication.py`
Comprehensive test for both JWT and API token authentication.

```bash
python backend/scripts/test_mcp_authentication.py
```

Tests:
- Login and JWT token generation
- Server API token generation
- MCP access with JWT token
- MCP access with API token (header)
- MCP access with API token (query param)
- Invalid token rejection
- No token rejection

#### `test_token_api.py`
Test the token API endpoints (generate, retrieve, revoke).

```bash
python backend/scripts/test_token_api.py
```

#### `test_mcp_auth.py`
Quick authentication test.

```bash
python backend/scripts/test_mcp_auth.py
```

### Database Management

#### `test_db_token.py`
Test database token retrieval.

```bash
python backend/scripts/test_db_token.py
```

Verifies that server API tokens can be retrieved from the database.

#### `debug_mcp_access.py`
Debug MCP access configuration and permissions.

```bash
python backend/scripts/debug_mcp_access.py
```

Shows:
- Server existence
- API token status
- User permissions
- Access control details

#### `setup_test_user.py`
Create or update test users.

```bash
python backend/scripts/setup_test_user.py
```

### UiPath Integration

#### `debug_uipath_api.py`
Debug UiPath API connectivity and authentication.

```bash
python backend/scripts/debug_uipath_api.py
```

Tests:
- UiPath API connection
- Folder listing
- Process listing
- Authentication

#### `test_uipath_processes.py`
Test UiPath process listing with folder context.

```bash
python backend/scripts/test_uipath_processes.py
```

#### `test_arguments_parsing.py`
Test UiPath process arguments parsing logic.

```bash
python backend/scripts/test_arguments_parsing.py
```

### Connection Testing

#### `test_live_connection.py`
Test live MCP connection with server API token.

```bash
python backend/scripts/test_live_connection.py
```

Requires the backend server to be running.

#### `test_specific_token.sh`
Bash script to test with a specific token.

```bash
bash backend/scripts/test_specific_token.sh
```

#### `test_mcp_connection.sh`
Interactive bash script for testing MCP connections.

```bash
bash backend/scripts/test_mcp_connection.sh
```

---

## Common Issues

### ModuleNotFoundError

```
ModuleNotFoundError: No module named 'src'
```

**Solution**: Run from project root, not from `backend/` or `backend/scripts/`.

```bash
# Wrong
cd backend/scripts
python test_db_token.py

# Correct
cd /path/to/uipath-mcp
python backend/scripts/test_db_token.py
```

### Database Not Found

```
sqlite3.OperationalError: unable to open database file
```

**Solution**: Ensure you're running from project root and the database exists at `backend/database/mcp_servers.db`.

```bash
# Check database exists
ls -la backend/database/mcp_servers.db

# Run from project root
python backend/scripts/script_name.py
```

### Import Errors

```
ImportError: cannot import name 'Database' from 'database'
```

**Solution**: The scripts add `backend/src` to the Python path. Make sure you're running from project root.

---

## Environment Setup

Some scripts require environment variables:

```bash
# UiPath configuration (for UiPath-related scripts)
export UIPATH_URL="https://cloud.uipath.com/org/tenant"
export UIPATH_ACCESS_TOKEN="your_pat_token"
export UIPATH_FOLDER_PATH="/Production"

# Database path (optional, defaults to backend/database/mcp_servers.db)
export DB_PATH="backend/database/mcp_servers.db"

# Server URL (for connection tests)
export SERVER_URL="http://localhost:8000"
```

---

## Running the Backend Server

Before running connection tests, start the backend server:

```bash
# From project root
python backend/src/main.py

# Or with uvicorn directly
python -m uvicorn src.http_server:app --host 0.0.0.0 --port 8000 --app-dir backend
```

---

## Creating New Scripts

When creating new scripts in this directory:

1. **Add path setup** at the top:
   ```python
   import sys
   sys.path.insert(0, 'backend/src')
   ```

2. **Use relative paths** from project root:
   ```python
   db = Database("backend/database/mcp_servers.db")
   ```

3. **Document in this README** with:
   - Purpose
   - Usage example
   - Required environment variables (if any)

4. **Add execution instructions**:
   ```python
   if __name__ == "__main__":
       # Your code here
   ```

---

## Quick Reference

| Script | Purpose | Requires Server |
|--------|---------|----------------|
| `test_mcp_authentication.py` | Full auth test | Yes |
| `test_token_api.py` | Token API test | Yes |
| `test_db_token.py` | DB token check | No |
| `debug_mcp_access.py` | Access debug | No |
| `debug_uipath_api.py` | UiPath API test | No |
| `test_live_connection.py` | Live connection | Yes |
| `setup_test_user.py` | Create users | No |

---

## Getting Help

If you encounter issues:

1. **Check working directory**: `pwd` should show project root
2. **Check database exists**: `ls backend/database/mcp_servers.db`
3. **Check Python path**: Scripts should add `backend/src` to path
4. **Check server running**: For connection tests, server must be running
5. **Check environment variables**: Some scripts need UiPath credentials

For more help, see the main project README or documentation.
