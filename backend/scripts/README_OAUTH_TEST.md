# OAuth Credentials Test Script

This script tests if your OAuth credentials (Client ID and Client Secret) can successfully authenticate with UiPath Identity server.

## Usage

### Method 1: Interactive Mode

Simply run the script and enter credentials when prompted:

```bash
cd backend
python scripts/test_oauth_credentials.py
```

You'll be prompted for:
- UiPath URL
- OAuth Client ID
- OAuth Client Secret

### Method 2: Environment Variables

Set environment variables and run:

```bash
cd backend

# Set credentials
export UIPATH_URL="https://your-server.com/org/tenant"
export UIPATH_CLIENT_ID="your-client-id"
export UIPATH_CLIENT_SECRET="your-client-secret"

# Run test
python scripts/test_oauth_credentials.py
```

### Method 3: One-liner

```bash
cd backend
UIPATH_URL="https://your-server.com/org/tenant" \
UIPATH_CLIENT_ID="your-client-id" \
UIPATH_CLIENT_SECRET="your-client-secret" \
python scripts/test_oauth_credentials.py
```

## Optional Parameters

You can also set optional OAuth parameters:

```bash
export UIPATH_OAUTH_SCOPE="OR.Folders.Read OR.Releases.Read OR.Jobs.Read"
export UIPATH_OAUTH_AUDIENCE="https://orchestrator.uipath.com"
```

## Example Output

### Successful Authentication

```
======================================================================
UiPath OAuth Credentials Test
======================================================================

Configuration:
  URL:       https://your-server.com/org/tenant
  Client ID: abc123-def456-ghi789
  Secret:    ********************

Attempting to obtain OAuth access token...
----------------------------------------------------------------------

✅ SUCCESS! OAuth token obtained successfully.
----------------------------------------------------------------------

Token Response:
  Access Token: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOi...
  Token Type:   Bearer
  Expires In:   3600 seconds
  Scope:        OR.Folders.Read OR.Releases.Read OR.Jobs.Read

======================================================================
✅ OAuth credentials are VALID and working!
======================================================================
```

### Failed Authentication

```
======================================================================
UiPath OAuth Credentials Test
======================================================================

Configuration:
  URL:       https://your-server.com/org/tenant
  Client ID: invalid-client-id
  Secret:    ********************

Attempting to obtain OAuth access token...
----------------------------------------------------------------------

❌ AUTHENTICATION FAILED: Failed to obtain OAuth token from Identity endpoints. Last error: HTTP 401: invalid_client

Possible issues:
  1. Invalid client_id or client_secret
  2. OAuth application not configured in UiPath
  3. Incorrect UiPath URL
  4. Network connectivity issues
  5. Identity server endpoint not accessible
```

## What This Script Tests

1. **URL Parsing**: Validates the UiPath URL format
2. **Endpoint Discovery**: Tries multiple Identity server endpoints:
   - `/identity/connect/token` (MSI On-Premise)
   - `/<path>/identity/connect/token` (MSI On-Premise with path)
   - `/identity_/connect/token` (Cloud & Automation Suite)
3. **OAuth Flow**: Performs client_credentials grant type
4. **Token Validation**: Verifies access_token is returned
5. **SSL Handling**: Works with self-signed certificates

## Troubleshooting

### Error: "invalid_client"
- Check that Client ID and Client Secret are correct
- Verify OAuth application is enabled in UiPath
- Ensure the application has the correct grant type (client_credentials)

### Error: "Connection refused" or "Timeout"
- Check network connectivity to UiPath server
- Verify firewall rules allow HTTPS traffic
- Confirm the URL is correct and accessible

### Error: "SSL certificate verify failed"
- The script automatically disables SSL verification for self-signed certificates
- If you still see this error, check your Python SSL configuration

### Error: "No access_token present"
- The Identity server responded but didn't return a token
- Check OAuth application configuration in UiPath
- Verify required scopes are configured

## Creating OAuth Application in UiPath

### For UiPath Cloud:
1. Go to Admin → External Applications
2. Click "Add Application"
3. Select "Confidential Application"
4. Set Application Type: "Non-interactive"
5. Configure scopes (e.g., OR.Folders, OR.Releases, OR.Jobs)
6. Save and copy Client ID and Client Secret

### For UiPath On-Premise:
1. Go to Admin → Security → External Applications
2. Click "Add Application"
3. Configure application settings
4. Set Grant Type: "Client Credentials"
5. Configure required scopes
6. Save and copy Client ID and Client Secret

## Exit Codes

- `0`: Success - OAuth credentials are valid
- `1`: Failure - Authentication failed or error occurred

This makes the script suitable for CI/CD pipelines and automated testing.
