# UiPath OAuth curl Examples

This document provides curl command examples for testing UiPath OAuth authentication.

## Basic curl Command

### Minimal Example (Cloud & Automation Suite)

```bash
curl -k -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=" \
  "https://cloud.uipath.com/identity_/connect/token"
```

### With Scope and Audience

```bash
curl -k -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=OR.Folders.Read OR.Releases.Read OR.Jobs.Read" \
  -d "audience=https://orchestrator.uipath.com" \
  "https://cloud.uipath.com/identity_/connect/token"
```

## Endpoint Variations

### 1. Cloud & Automation Suite
```bash
curl -k -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=" \
  "https://cloud.uipath.com/identity_/connect/token"
```

### 2. MSI On-Premise (Base URL)
```bash
curl -k -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=" \
  "https://your-server.com/identity/connect/token"
```

### 3. MSI On-Premise (With Organization Path)
```bash
curl -k -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=" \
  "https://your-server.com/org/tenant/identity/connect/token"
```

## Using the Shell Script

We provide a convenient shell script that tries all endpoints automatically:

### Basic Usage
```bash
./backend/scripts/test_oauth_curl.sh \
  -u "https://your-server.com/org/tenant" \
  -i "your-client-id" \
  -s "your-client-secret"
```

### With Environment Variables
```bash
export UIPATH_URL="https://your-server.com/org/tenant"
export UIPATH_CLIENT_ID="your-client-id"
export UIPATH_CLIENT_SECRET="your-client-secret"

./backend/scripts/test_oauth_curl.sh
```

### With Custom Scope
```bash
./backend/scripts/test_oauth_curl.sh \
  -u "https://cloud.uipath.com/org/tenant" \
  -i "client-id" \
  -s "client-secret" \
  -S "OR.Folders.Read OR.Releases.Read"
```

### Verbose Mode
```bash
./backend/scripts/test_oauth_curl.sh \
  -u "https://your-server.com/org/tenant" \
  -i "client-id" \
  -s "client-secret" \
  -v
```

### Test Specific Endpoint
```bash
./backend/scripts/test_oauth_curl.sh \
  -u "https://your-server.com" \
  -i "client-id" \
  -s "client-secret" \
  -e "/identity/connect/token"
```

## Understanding the Request

### Request Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `grant_type` | Yes | Must be `client_credentials` |
| `client_id` | Yes | OAuth Client ID from UiPath |
| `client_secret` | Yes | OAuth Client Secret from UiPath |
| `scope` | No | Space-separated scopes (e.g., `OR.Folders.Read`) |
| `audience` | No | Target audience (e.g., `https://orchestrator.uipath.com`) |

### Request Headers

```
Content-Type: application/x-www-form-urlencoded
```

### curl Options

- `-k` or `--insecure`: Skip SSL certificate verification (for self-signed certs)
- `-X POST`: HTTP POST method
- `-H`: Add header
- `-d`: Add form data
- `-s`: Silent mode (no progress bar)
- `-w`: Write out format (for extracting HTTP status code)

## Expected Response

### Success (HTTP 200)

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "OR.Folders.Read OR.Releases.Read OR.Jobs.Read"
}
```

### Error Responses

#### Invalid Client (HTTP 401)
```json
{
  "error": "invalid_client",
  "error_description": "Client authentication failed"
}
```

#### Invalid Scope (HTTP 400)
```json
{
  "error": "invalid_scope",
  "error_description": "The requested scope is invalid"
}
```

#### Server Error (HTTP 500)
```json
{
  "error": "server_error",
  "error_description": "An internal server error occurred"
}
```

## Using the Token

Once you have the access token, use it in API requests:

```bash
# Get folders
curl -k -X GET \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "https://your-server.com/org/tenant/orchestrator_/odata/Folders"

# Get releases
curl -k -X GET \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-UIPATH-OrganizationUnitId: FOLDER_ID" \
  "https://your-server.com/org/tenant/orchestrator_/odata/Releases"

# Start job
curl -k -X POST \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-UIPATH-OrganizationUnitId: FOLDER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "startInfo": {
      "ReleaseKey": "release-key",
      "Strategy": "Specific",
      "RobotIds": [],
      "NoOfRobots": 0,
      "Source": "Manual",
      "InputArguments": "{\"param1\":\"value1\"}"
    }
  }' \
  "https://your-server.com/org/tenant/orchestrator_/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs"
```

## Troubleshooting

### SSL Certificate Issues

If you see SSL certificate errors:
```bash
# Add -k flag to skip verification
curl -k ...
```

### Connection Timeout

If the request times out:
```bash
# Add timeout options
curl --connect-timeout 10 --max-time 30 ...
```

### Verbose Debugging

To see full request/response details:
```bash
curl -v ...
```

### Save Response to File

```bash
curl -k -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=" \
  "https://your-server.com/identity/connect/token" \
  -o response.json
```

## Comparison with oauth.py

The shell script (`test_oauth_curl.sh`) implements the same logic as `oauth.py`:

1. **Endpoint Discovery**: Tries multiple Identity endpoints in order
2. **SSL Handling**: Disables verification for self-signed certificates
3. **Error Handling**: Provides detailed error messages
4. **Token Validation**: Checks for `access_token` in response

The main difference is that the shell script is standalone and doesn't require Python dependencies.
