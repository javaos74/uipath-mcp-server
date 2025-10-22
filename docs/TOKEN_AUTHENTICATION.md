# Token Authentication Guide

## Overview

This system uses JWT (JSON Web Token) based authentication. After logging in,
users receive a token which they use to access the API.

## Authentication Flow

### 1. User Registration

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "email": "john@example.com",
    "password": "password123",
    "role": "user"
  }'
```

**Response:**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "uipath_url": null,
  "uipath_folder_path": null,
  "created_at": "2025-10-18 09:00:00",
  "updated_at": "2025-10-18 09:00:00"
}
```

### 2. Login and Issue Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "password": "password123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "role": "user",
    "is_active": true,
    "uipath_url": null,
    "uipath_folder_path": null,
    "created_at": "2025-10-18 09:00:00",
    "updated_at": "2025-10-18 09:00:00"
  }
}
```

### 3. Use the Token

Include the `access_token` in the `Authorization` header of all API requests:

```bash
curl -X GET http://localhost:8000/api/servers \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## How to Store Tokens

### Web Browser

```javascript
// Store token after login
const response = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'john', password: 'password123' })
});

const data = await response.json();
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('user', JSON.stringify(data.user));

// Use token for API calls
const serversResponse = await fetch('http://localhost:8000/api/servers', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});
```

### Python Script

```python
import requests
import os

# Login
response = requests.post('http://localhost:8000/auth/login', json={
    'username': 'john',
    'password': 'password123'
})

data = response.json()
token = data['access_token']

# Optionally store in environment variable
os.environ['MCP_TOKEN'] = token

# API call
headers = {'Authorization': f'Bearer {token}'}
servers = requests.get('http://localhost:8000/api/servers', headers=headers)
print(servers.json())
```

### CLI Tool

```bash
# Save token to a file
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"john","password":"password123"}' \
  | jq -r '.access_token' > ~/.mcp_token

# Use saved token
TOKEN=$(cat ~/.mcp_token)
curl -X GET http://localhost:8000/api/servers \
  -H "Authorization: Bearer $TOKEN"
```

## UiPath Configuration

### Save UiPath PAT

Users can save their UiPath Personal Access Token:

```bash
curl -X PUT http://localhost:8000/auth/uipath-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "uipath_url": "https://cloud.uipath.com/myaccount/mytenant",
    "uipath_access_token": "YOUR_UIPATH_PAT",
    "uipath_folder_path": "/Production/Finance"
  }'
```

**Response:**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "uipath_url": "https://cloud.uipath.com/myaccount/mytenant",
  "uipath_folder_path": "/Production/Finance",
  "created_at": "2025-10-18 09:00:00",
  "updated_at": "2025-10-18 09:05:00"
}
```

**Note:** For security reasons, `uipath_access_token` is not included in the
response.

### Use UiPath PAT

Once a user saves their UiPath configuration, their UiPath credentials are
automatically used when Tools run on MCP servers created by that user.

## Token Expiration

- JWT tokens are valid for **24 hours**
- When the token expires, you must log in again
- If you receive a 401 Unauthorized response, the token has expired or is
  invalid

## Security Recommendations

1. **Use HTTPS** in production environments
2. **Change SECRET_KEY**: Set a strong random value for `SECRET_KEY` in `.env`
   ```bash
   openssl rand -hex 32
   ```
3. **Store tokens securely**:
   - Browser: Prefer httpOnly cookies over localStorage
   - Server: Use environment variables or a secure vault
4. **Prevent token leakage**:
   - Do not print tokens in logs
   - Do not commit tokens to Git
   - Do not share tokens in public channels

## Login Screen Example

### HTML + JavaScript

```html
<!DOCTYPE html>
<html>
<head>
    <title>MCP Server Login</title>
</head>
<body>
    <h1>Login</h1>
    <form id="loginForm">
        <input type="text" id="username" placeholder="Username" required>
        <input type="password" id="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    <div id="message"></div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('http://localhost:8000/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    
                    document.getElementById('message').textContent = 'Login successful!';
                    // Redirect to dashboard
                    window.location.href = '/dashboard.html';
                } else {
                    const error = await response.json();
                    document.getElementById('message').textContent = error.error;
                }
            } catch (error) {
                document.getElementById('message').textContent = 'Login failed: ' + error.message;
            }
        });
    </script>
</body>
</html>
```

## API Endpoints

### Authentication

- `POST /auth/register` - Register a user
- `POST /auth/login` - Login (issues token)
- `GET /auth/me` - Get current user info (requires auth)
- `PUT /auth/uipath-config` - Update UiPath config (requires auth)

### Protected Endpoints

All `/api/*` and `/mcp/*` endpoints require authentication.
