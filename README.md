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

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info
- `PUT /auth/uipath-config` - Update UiPath configuration

### MCP Servers
- `GET /api/servers` - List servers
- `POST /api/servers` - Create server
- `GET /api/servers/{tenant}/{server}` - Get server details
- `PUT /api/servers/{tenant}/{server}` - Update server
- `DELETE /api/servers/{tenant}/{server}` - Delete server

### MCP Tools
- `GET /api/servers/{tenant}/{server}/tools` - List tools
- `POST /api/servers/{tenant}/{server}/tools` - Create tool
- `GET /api/servers/{tenant}/{server}/tools/{tool}` - Get tool
- `PUT /api/servers/{tenant}/{server}/tools/{tool}` - Update tool
- `DELETE /api/servers/{tenant}/{server}/tools/{tool}` - Delete tool

### MCP Protocol
- `GET /mcp/{tenant}/{server}/sse` - SSE connection
- `POST /mcp/{tenant}/{server}` - HTTP Streamable

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
- `LOG_LEVEL` - Logging level (default: INFO)

## License

MIT
