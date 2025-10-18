# MCP Client Setup Guide

## How to Connect External MCP Clients

Your MCP server requires authentication. Follow these steps to connect external clients like Claude Desktop or Cline.

### Step 1: Get Your Access Token

1. Login to the web interface
2. Open browser DevTools (F12)
3. Go to Application/Storage → Local Storage
4. Find the `token` key and copy its value

Or use the API to get a token:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

The response will contain an `access_token`.

### Step 2: Configure Your MCP Client

#### For Claude Desktop (macOS)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "uipath-server": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-everything"
      ],
      "env": {
        "MCP_SERVER_URL": "http://localhost:8000/mcp/UiPath/CharlesTest",
        "MCP_AUTH_TOKEN": "YOUR_ACCESS_TOKEN_HERE"
      }
    }
  }
}
```

#### For Cline VSCode Extension

Add to your Cline MCP settings:

```json
{
  "mcpServers": {
    "uipath-server": {
      "url": "http://localhost:8000/mcp/UiPath/CharlesTest",
      "headers": {
        "Authorization": "Bearer YOUR_ACCESS_TOKEN_HERE"
      }
    }
  }
}
```

#### Using curl for testing

```bash
# Test the connection
curl -N -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  http://localhost:8000/mcp/UiPath/CharlesTest
```

### Step 3: Verify Connection

Check the server logs to see if the connection is successful. You should see:
- No 403 Forbidden errors
- SSE connection established
- MCP protocol messages being exchanged

## Troubleshooting

### 403 Forbidden Error
- **Cause**: Missing or invalid authentication token
- **Solution**: Make sure you're sending the `Authorization: Bearer <token>` header

### 401 Unauthorized Error
- **Cause**: Token expired or invalid
- **Solution**: Get a new token by logging in again

### 404 Not Found Error
- **Cause**: Server doesn't exist
- **Solution**: Check the tenant_name and server_name in the URL

### Connection Timeout
- **Cause**: Server not running or wrong URL
- **Solution**: Verify the server is running on the correct port

## Security Notes

- Keep your access token secure
- Tokens expire after a certain period (check your server configuration)
- Don't share tokens or commit them to version control
- Use environment variables for tokens in production
