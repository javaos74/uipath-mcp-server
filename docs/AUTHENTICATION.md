# MCP Server Authentication Guide

## Quick Start

**For External MCP Clients (Claude Desktop, Cline, etc.):**

1. Login to web UI: `http://localhost:8000`
2. Go to your server's detail page (e.g., "CharlesTest" under "UiPath")
3. Click **"Generate Token"** in the API Token section
4. Click **"Show"** and **"Copy"** the token
5. Use in your MCP client:
   ```
   http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_TOKEN_HERE
   ```

That's it! Your MCP client can now connect to the server.

---

## Overview

The MCP server requires authentication for all endpoints, including the SSE (Server-Sent Events) endpoint used by MCP clients.

**Authentication happens at the MCP endpoint:** `/mcp/{tenant_name}/{server_name}`

Every request to this endpoint must include a valid token (Server API Token or JWT Token).

## Two Authentication Methods

The MCP server supports **two types of tokens**:

### 1. Server API Token (Recommended for External Clients)
- **Purpose**: For external MCP clients (Claude Desktop, Cline, etc.)
- **Scope**: Access to a specific MCP server only
- **Generation**: Created in the web UI for each server
- **Lifetime**: Does not expire (until revoked)
- **Security**: Can be revoked and regenerated at any time

### 2. JWT Token (User Authentication)
- **Purpose**: For web UI and API management
- **Scope**: Access to all servers owned by the user
- **Generation**: Obtained by logging in
- **Lifetime**: Expires after 30 days (configurable)
- **Security**: Tied to user account

## Using MCP Server API Token (Recommended for External Clients)

### Step-by-Step Guide

#### 1. Generate API Token in Web UI

1. Login to the web interface at `http://localhost:8000`
2. Navigate to your MCP server's detail page
   - Example: Click on "CharlesTest" server under "UiPath" tenant
3. Find the **"API Token"** section (displayed prominently at the top)
4. Click **"Generate Token"** button
   - If a token already exists, you'll be asked to confirm regeneration
5. Click **"Show"** button to reveal the token
6. Click **"Copy"** button to copy the token to clipboard

#### 2. Use Token to Access MCP Endpoint

The MCP endpoint URL format is:
```
http://localhost:8000/mcp/{tenant_name}/{server_name}
```

Example:
```
http://localhost:8000/mcp/UiPath/CharlesTest
```

**Method A: Authorization Header (Recommended)**
```bash
curl -N -H "Authorization: Bearer YOUR_API_TOKEN_HERE" \
  http://localhost:8000/mcp/UiPath/CharlesTest
```

**Method B: Query Parameter**
```bash
curl -N "http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_API_TOKEN_HERE"
```

#### 3. Token Management

- **Regenerate**: Click "Regenerate" to create a new token (invalidates the old one)
- **Revoke**: Click "Revoke" to delete the token (blocks all access using that token)
- **Copy**: Click "Copy" to copy the token to clipboard

### Authentication Flow

When you access `/mcp/{tenant_name}/{server_name}`:

1. **Server extracts token** from:
   - `Authorization: Bearer <token>` header, OR
   - `?token=<token>` query parameter

2. **Server validates token** by checking:
   - Is it a valid Server API Token for this specific server? → ✅ Access granted
   - Is it a valid JWT Token for a user who owns this server? → ✅ Access granted
   - Otherwise → ❌ 403 Forbidden

3. **Access granted** - SSE connection established for MCP protocol

### Example: Complete Workflow

```bash
# 1. Login to get JWT token (for management)
JWT_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Generate server API token
API_TOKEN=$(curl -s -X POST http://localhost:8000/api/servers/UiPath/CharlesTest/token \
  -H "Authorization: Bearer $JWT_TOKEN" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

echo "API Token: $API_TOKEN"

# 3. Use API token to access MCP endpoint
curl -N -H "Authorization: Bearer $API_TOKEN" \
  http://localhost:8000/mcp/UiPath/CharlesTest

# Or with query parameter
curl -N "http://localhost:8000/mcp/UiPath/CharlesTest?token=$API_TOKEN"
```

## 403 Forbidden Error

If you see a `403 Forbidden` error when connecting to `/mcp/{tenant_name}/{server_name}`, it means:

1. **No authentication token provided** - You need to include a valid Server API token or JWT token
2. **Invalid token** - The token is expired, malformed, or doesn't match the server
3. **Access denied** - The JWT token belongs to a user who doesn't own this server (and is not an admin)
4. **Server not found** - The tenant_name or server_name is incorrect

## Authentication Methods

The server supports **two methods** for providing authentication tokens:

### Method 1: Authorization Header (Recommended)

Send the token in the `Authorization` header:

```bash
curl -N -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  http://localhost:8000/mcp/UiPath/CharlesTest
```

**Pros:**
- Standard HTTP authentication
- More secure (not visible in URLs)
- Supported by most HTTP clients

**Cons:**
- Some MCP clients may not support custom headers

### Method 2: Query Parameter

Send the token as a query parameter:

```bash
curl -N "http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_TOKEN_HERE"
```

**Pros:**
- Works with clients that don't support custom headers
- Simple to use

**Cons:**
- Token visible in URL (less secure)
- May be logged in server access logs

## Getting Your Tokens

### Server API Token (For MCP Clients)

**Via Web Interface (Recommended):**

1. Login to the web interface
2. Navigate to your server's detail page
3. Find the "API Token" section
4. Click "Generate Token"
5. Click "Show" to reveal the token
6. Click "Copy" to copy to clipboard

**Via API:**

```bash
# First, login to get JWT token
JWT_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Generate server API token
curl -X POST http://localhost:8000/api/servers/UiPath/CharlesTest/token \
  -H "Authorization: Bearer $JWT_TOKEN"
```

Response:
```json
{
  "token": "abc123def456...",
  "message": "API token generated successfully"
}
```

### JWT Token (For Management)

**Via Web Interface:**

1. Login to the web interface
2. Open browser DevTools (F12)
3. Go to **Application** → **Local Storage**
4. Find the `token` key
5. Copy the token value

**Via API:**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "your_username",
    ...
  }
}
```

## Testing Your Connection

### Using Python Script (Comprehensive Test)

```bash
python backend/scripts/test_mcp_authentication.py
```

This interactive script will:
1. Login and get JWT token
2. Generate server API token
3. Test MCP access with JWT token
4. Test MCP access with API token (header)
5. Test MCP access with API token (query param)
6. Test invalid token (should fail)
7. Test no token (should fail)

### Quick Test

```bash
python backend/scripts/test_mcp_auth.py
```

This script will:
1. Prompt for your credentials
2. Get an access token
3. Test both authentication methods
4. Show you the exact URLs to use

### Using Bash Script

```bash
bash backend/scripts/test_mcp_connection.sh
```

### Manual Testing with curl

```bash
# 1. Login and get token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Test with Authorization header
curl -N -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/mcp/UiPath/CharlesTest

# 3. Test with query parameter
curl -N "http://localhost:8000/mcp/UiPath/CharlesTest?token=$TOKEN"
```

## Configuring MCP Clients

### Important: Use Server API Token

For external MCP clients, **always use the Server API Token** (not JWT token):
- ✅ Server API Token: Generated in web UI, never expires
- ❌ JWT Token: Expires after 30 days, requires re-login

### Claude Desktop

**Step 1: Get your Server API Token**
1. Login to web UI
2. Go to your server's detail page
3. Generate and copy the API token

**Step 2: Configure Claude Desktop**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "uipath-charlestest": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"],
      "env": {
        "FETCH_URL": "http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_SERVER_API_TOKEN_HERE"
      }
    }
  }
}
```

**Alternative with Authorization Header:**

If your MCP client supports custom headers, use this format:

```json
{
  "mcpServers": {
    "uipath-charlestest": {
      "url": "http://localhost:8000/mcp/UiPath/CharlesTest",
      "headers": {
        "Authorization": "Bearer YOUR_SERVER_API_TOKEN_HERE"
      }
    }
  }
}
```

### Cline VSCode Extension

**Step 1: Get your Server API Token** (same as above)

**Step 2: Configure Cline**

Add to your Cline MCP settings:

```json
{
  "mcpServers": {
    "uipath-charlestest": {
      "url": "http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_SERVER_API_TOKEN_HERE"
    }
  }
}
```

### Custom MCP Client

If you're building a custom MCP client, use the Server API Token:

**JavaScript/TypeScript Example:**

```javascript
// Method 1: Query Parameter (works with standard EventSource)
const eventSource = new EventSource(
  'http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_SERVER_API_TOKEN_HERE'
);

eventSource.onmessage = (event) => {
  console.log('Received:', event.data);
};

// Method 2: Authorization Header (requires custom implementation)
const response = await fetch('http://localhost:8000/mcp/UiPath/CharlesTest', {
  headers: {
    'Authorization': 'Bearer YOUR_SERVER_API_TOKEN_HERE'
  }
});
```

**Python Example:**

```python
import requests

# Method 1: Authorization Header
response = requests.get(
    'http://localhost:8000/mcp/UiPath/CharlesTest',
    headers={'Authorization': 'Bearer YOUR_SERVER_API_TOKEN_HERE'},
    stream=True
)

# Method 2: Query Parameter
response = requests.get(
    'http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_SERVER_API_TOKEN_HERE',
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

### Using SSE Directly

Standard EventSource only supports query parameters (no custom headers):

```javascript
// ✅ This works
const eventSource = new EventSource(
  'http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_SERVER_API_TOKEN_HERE'
);

// ❌ This doesn't work (EventSource doesn't support custom headers)
const eventSource = new EventSource(
  'http://localhost:8000/mcp/UiPath/CharlesTest',
  {
    headers: {
      'Authorization': 'Bearer YOUR_SERVER_API_TOKEN_HERE'
    }
  }
);
```

For Authorization header support, use fetch or a custom SSE library.

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_TOKEN_HERE'
);
```

## Troubleshooting

### 403 Forbidden

**Error message:**
```json
{
  "error": "Access denied. Please provide a valid authentication token via Authorization header or ?token= query parameter."
}
```

**Solutions:**
1. Make sure you're sending a valid token
2. Check that the token hasn't expired
3. Verify you own the server (or are an admin)
4. Ensure the server exists in the database

### 401 Unauthorized

**Cause:** Token is invalid or expired

**Solution:** Get a new token by logging in again

### 404 Not Found

**Cause:** Server doesn't exist

**Solution:** 
1. Check the URL format: `/mcp/{tenant_name}/{server_name}`
2. Verify the server exists in the web interface
3. Make sure you're using the correct tenant and server names

## Security Best Practices

1. **Never commit tokens** to version control
2. **Use environment variables** for tokens in production
3. **Rotate tokens regularly** by logging in again
4. **Use Authorization header** instead of query parameters when possible
5. **Use HTTPS** in production to encrypt tokens in transit
6. **Keep tokens secure** - treat them like passwords

## Token Expiration

### Server API Token
- **Does NOT expire** - Valid until revoked
- Revoke and regenerate in the web UI if compromised
- Each server has its own independent token

### JWT Token
- **Expires after 30 days** (configurable)
- When expired, you'll get a 401 Unauthorized error
- Login again to get a new token
- Used for web UI and management operations

## Admin Access

Admin users can access all MCP servers, regardless of ownership. Regular users can only access servers they created.

To check if you're an admin:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/auth/me
```

Look for `"role": "admin"` in the response.


## Frequently Asked Questions (FAQ)

### Q: Which token should I use for my MCP client?

**A:** Use the **Server API Token** generated in the web UI for each server.
- ✅ Server API Token: Never expires, server-specific, easy to manage
- ❌ JWT Token: Expires after 30 days, requires re-login

### Q: How do I get the Server API Token?

**A:** 
1. Login to web UI at `http://localhost:8000`
2. Navigate to your server's detail page
3. Find "API Token" section
4. Click "Generate Token"
5. Click "Show" and "Copy"

### Q: Can I use the same token for multiple servers?

**A:** No. Each server has its own unique API token. This provides better security and isolation.

### Q: What happens if I regenerate the token?

**A:** The old token is immediately invalidated. Any MCP clients using the old token will get 403 Forbidden errors. Update your clients with the new token.

### Q: How do I revoke access to a server?

**A:** Click "Revoke" in the API Token section. This deletes the token and blocks all access using that token. You can generate a new token later.

### Q: Can I use the token in the URL?

**A:** Yes, but it's less secure:
- ✅ Recommended: `Authorization: Bearer <token>` header
- ⚠️  Less secure: `?token=<token>` query parameter (visible in logs)

### Q: What's the difference between Server API Token and JWT Token?

| Feature | Server API Token | JWT Token |
|---------|-----------------|-----------|
| Purpose | MCP client access | User authentication |
| Scope | One specific server | All user's servers |
| Expiration | Never (until revoked) | 30 days |
| Generation | Web UI per server | Login API |
| Use case | External clients | Web UI, management |

### Q: How do I test if my token works?

**A:** Use curl:
```bash
# Test with your token
curl -N -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/mcp/UiPath/CharlesTest

# Or with query parameter
curl -N "http://localhost:8000/mcp/UiPath/CharlesTest?token=YOUR_TOKEN"
```

If you see a 200 OK or SSE stream, it works!

### Q: I'm getting 403 Forbidden. What should I check?

**A:** Check these in order:
1. ✅ Token is included in request (header or query param)
2. ✅ Token is correct (copy-paste from web UI)
3. ✅ Server exists (check tenant_name and server_name in URL)
4. ✅ Token hasn't been revoked (check web UI)
5. ✅ You're using the Server API Token (not JWT token)

### Q: Can I share my token with others?

**A:** 
- ⚠️  Server API Token: Yes, but only with trusted users. Anyone with the token can access that specific server.
- ❌ JWT Token: No, it's tied to your user account and gives access to all your servers.

### Q: How do I rotate tokens for security?

**A:**
1. Generate a new token in web UI (old token still works)
2. Update all MCP clients with new token
3. Test that clients work with new token
4. Revoke old token (or just regenerate to auto-revoke)

### Q: Does the token work over the internet?

**A:** Yes, but:
- Use HTTPS in production (not HTTP)
- Consider using a reverse proxy with rate limiting
- Monitor token usage for suspicious activity
- Rotate tokens regularly

### Q: Can I see which token was used to access my server?

**A:** Currently, the server logs show access attempts. Check server logs for authentication events. Future versions may include an audit log in the web UI.
