# UiPath MCP Server

UiPath On-Premise MCP Server with Web UI for managing multiple MCP endpoints.

## Architecture

- **Backend**: Python (FastAPI/Starlette) - MCP server with authentication
- **Frontend**: React + TypeScript (Vite) - Web UI for server management
- **Database**: SQLite - User, server, and tool configuration

## Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- uv (Python package manager)

### Backend Development

```bash
cd backend
uv sync
uv run python -m src.main
```

Backend runs on `http://localhost:8000`

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server runs on `http://localhost:3000` with API proxy to backend.

## Production Build

### Build Frontend and Run

```bash
# Build frontend (outputs to backend/static/)
./build.sh

# Run backend (serves both API and frontend)
cd backend
uv run python -m src.main
```

Access the application at `http://localhost:8000`

### Docker Deployment

```bash
# 1. Build frontend first
./build.sh

# 2. Build Docker image (uses version from pyproject.toml)
./docker-build-simple.sh

# 3. Run with Docker Compose
docker-compose up -d
```

Docker image will be tagged with the version from `backend/pyproject.toml` (currently: `0.1.0`).

See [DOCKER.md](DOCKER.md) for detailed Docker deployment guide.

### Manual Build

```bash
# Build frontend
cd frontend
npm install
npm run build

# Run backend
cd ../backend
uv run python -m src.main
```

## Features

- 🔐 **Multi-tenant Authentication** - User registration and JWT-based authentication
- 🤖 **Multiple MCP Servers** - Create and manage multiple MCP server endpoints
- 🔧 **Dynamic Tool Management** - Create tools mapped to UiPath processes
- 🔑 **Dual Authentication Support** - PAT (Personal Access Token) and OAuth 2.0
- 🌐 **Web UI** - React-based interface for easy management
- 📊 **Real-time Monitoring** - Track tool execution and job status
- 🔒 **Secure Token Management** - Generate and manage API tokens per server
- 🏢 **On-Premise Support** - Works with both UiPath Cloud and On-Premise installations

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
  ```json
  {
    "username": "user",
    "email": "user@example.com",
    "password": "password123"
  }
  ```
- `POST /auth/login` - Login and get JWT token
  ```json
  {
    "username": "user",
    "password": "password123"
  }
  ```
- `GET /auth/me` - Get current user info (requires JWT)
- `PUT /auth/uipath-config` - Update UiPath configuration
  ```json
  {
    "uipath_url": "https://cloud.uipath.com/org/tenant",
    "uipath_auth_type": "pat",
    "uipath_access_token": "your-pat-token"
  }
  ```
  Or for OAuth:
  ```json
  {
    "uipath_url": "https://your-server.com/org/tenant",
    "uipath_auth_type": "oauth",
    "uipath_client_id": "your-client-id",
    "uipath_client_secret": "your-client-secret"
  }
  ```

### MCP Servers
- `GET /api/servers` - List all servers for current user
- `POST /api/servers` - Create new MCP server
  ```json
  {
    "tenant_name": "MyTenant",
    "server_name": "MyServer",
    "description": "Server description"
  }
  ```
- `GET /api/servers/{tenant}/{server}` - Get server details
- `PUT /api/servers/{tenant}/{server}` - Update server
- `DELETE /api/servers/{tenant}/{server}` - Delete server

### Server Token Management
- `GET /api/servers/{tenant}/{server}/token` - Get current API token
- `POST /api/servers/{tenant}/{server}/token` - Generate new API token
- `DELETE /api/servers/{tenant}/{server}/token` - Revoke API token

### MCP Tools
- `GET /api/servers/{tenant}/{server}/tools` - List all tools
- `POST /api/servers/{tenant}/{server}/tools` - Create new tool
  ```json
  {
    "name": "my_tool",
    "description": "Tool description",
    "input_schema": {
      "type": "object",
      "properties": {
        "param1": {"type": "string"}
      },
      "required": ["param1"]
    },
    "uipath_process_name": "ProcessName",
    "uipath_folder_id": "folder-id"
  }
  ```
- `GET /api/servers/{tenant}/{server}/tools/{tool}` - Get tool details
- `PUT /api/servers/{tenant}/{server}/tools/{tool}` - Update tool
- `DELETE /api/servers/{tenant}/{server}/tools/{tool}` - Delete tool

### UiPath Integration
- `GET /api/uipath/folders` - List UiPath folders
- `GET /api/uipath/processes?folder_id={id}` - List processes in folder

### MCP Protocol
- `GET /mcp/{tenant}/{server}/sse` - SSE connection for MCP clients
- `POST /mcp/{tenant}/{server}/sse/messages` - SSE message posting
- `GET /mcp/{tenant}/{server}` - HTTP Streamable (GET)
- `POST /mcp/{tenant}/{server}` - HTTP Streamable (POST)
- `DELETE /mcp/{tenant}/{server}` - HTTP Streamable (DELETE)

**Authentication**: MCP endpoints require API token in header:
```
Authorization: Bearer <server-api-token>
```

### Health Check
- `GET /health` - Server health check endpoint

## UiPath Configuration

### Authentication Methods

The server supports two authentication methods for UiPath:

#### 1. Personal Access Token (PAT)
Best for UiPath Cloud environments:
- Generate PAT from UiPath Cloud Admin Console
- Configure in Settings page
- Suitable for: UiPath Cloud (cloud.uipath.com)

#### 2. OAuth 2.0 (Client Credentials)
Best for On-Premise installations:
- Create OAuth application in UiPath
- Get Client ID and Client Secret
- Configure in Settings page
- Suitable for: On-Premise UiPath installations with self-signed certificates

### SSL Certificate Handling

The server automatically handles self-signed certificates for On-Premise installations:
- SSL verification is disabled for non-cloud URLs
- SSL warnings are suppressed
- Works seamlessly with internal CA certificates

### Execution Methods

The server automatically selects the appropriate execution method:
- **UiPath Cloud** (`uipath.com` in URL): Uses UiPath Python SDK
- **On-Premise**: Uses REST API with `startJobs` endpoint

## Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
cd backend
cp .env.example .env
# Edit .env with your configuration
```

Available variables:
- `API_HOST` - Server host (default: 0.0.0.0)
- `API_PORT` - Server port (default: 8000)
- `DB_PATH` - Database file path (default: database/mcp_servers.db)
- `SECRET_KEY` - JWT secret key (required for production)
- `TOOL_CALL_TIMEOUT` - UiPath tool execution timeout in seconds (default: 600)
- `LOG_LEVEL` - Logging level (default: INFO)

## Usage Guide

### 1. Register and Login
1. Access the web UI at `http://localhost:8000`
2. Register a new account
3. Login with your credentials

### 2. Configure UiPath
1. Go to Settings page
2. Enter your UiPath URL
3. Choose authentication method:
   - **PAT**: Enter your Personal Access Token
   - **OAuth**: Enter Client ID and Client Secret
4. Save configuration

### 3. Create MCP Server
1. Go to Dashboard
2. Click "Create Server"
3. Enter tenant name and server name
4. Generate API token for the server

### 4. Add Tools
1. Select a server from the list
2. Click "Add Tool from UiPath"
3. Select folder and process
4. Configure tool parameters
5. Save tool

### 5. Use MCP Server
Configure your MCP client (e.g., Claude Desktop) with:
```json
{
  "mcpServers": {
    "uipath": {
      "url": "http://localhost:8000/mcp/MyTenant/MyServer/sse",
      "headers": {
        "Authorization": "Bearer <your-server-api-token>"
      }
    }
  }
}
```

## License

MIT
