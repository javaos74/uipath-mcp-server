#!/bin/bash
# UiPath OAuth Token Request using curl
# This script demonstrates how to obtain an OAuth access token using client credentials

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓ ${NC}$1"
}

print_error() {
    echo -e "${RED}✗ ${NC}$1"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${NC}$1"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Test UiPath OAuth authentication using curl.

OPTIONS:
    -u, --url URL              UiPath base URL (required)
    -i, --client-id ID         OAuth Client ID (required)
    -s, --client-secret SECRET OAuth Client Secret (required)
    -S, --scope SCOPE          OAuth scope (optional, default: empty)
    -a, --audience AUDIENCE    OAuth audience (optional)
    -e, --endpoint ENDPOINT    Specific endpoint to test (optional)
    -v, --verbose              Verbose output
    -h, --help                 Show this help message

EXAMPLES:
    # Basic usage
    $0 -u https://your-server.com/org/tenant \\
       -i your-client-id \\
       -s your-client-secret

    # With custom scope
    $0 -u https://cloud.uipath.com/org/tenant \\
       -i client-id \\
       -s client-secret \\
       -S "OR.Folders.Read OR.Releases.Read"

    # Test specific endpoint
    $0 -u https://your-server.com \\
       -i client-id \\
       -s client-secret \\
       -e "/identity/connect/token"

ENVIRONMENT VARIABLES:
    UIPATH_URL              UiPath base URL
    UIPATH_CLIENT_ID        OAuth Client ID
    UIPATH_CLIENT_SECRET    OAuth Client Secret
    UIPATH_OAUTH_SCOPE      OAuth scope
    UIPATH_OAUTH_AUDIENCE   OAuth audience

EOF
    exit 1
}

# Parse command line arguments
UIPATH_URL="${UIPATH_URL:-}"
CLIENT_ID="${UIPATH_CLIENT_ID:-}"
CLIENT_SECRET="${UIPATH_CLIENT_SECRET:-}"
SCOPE="${UIPATH_OAUTH_SCOPE:-}"
AUDIENCE="${UIPATH_OAUTH_AUDIENCE:-}"
SPECIFIC_ENDPOINT=""
VERBOSE=0

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            UIPATH_URL="$2"
            shift 2
            ;;
        -i|--client-id)
            CLIENT_ID="$2"
            shift 2
            ;;
        -s|--client-secret)
            CLIENT_SECRET="$2"
            shift 2
            ;;
        -S|--scope)
            SCOPE="$2"
            shift 2
            ;;
        -a|--audience)
            AUDIENCE="$2"
            shift 2
            ;;
        -e|--endpoint)
            SPECIFIC_ENDPOINT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [[ -z "$UIPATH_URL" ]]; then
    print_error "UiPath URL is required"
    usage
fi

if [[ -z "$CLIENT_ID" ]]; then
    print_error "Client ID is required"
    usage
fi

if [[ -z "$CLIENT_SECRET" ]]; then
    print_error "Client Secret is required"
    usage
fi

# Parse URL to extract base
if [[ "$UIPATH_URL" =~ ^(https?://[^/]+)(.*)$ ]]; then
    BASE_URL="${BASH_REMATCH[1]}"
    URL_PATH="${BASH_REMATCH[2]}"
else
    print_error "Invalid URL format: $UIPATH_URL"
    exit 1
fi

# Print configuration
echo "========================================================================"
echo "UiPath OAuth Token Request Test (curl)"
echo "========================================================================"
echo ""
print_info "Configuration:"
echo "  Base URL:      $BASE_URL"
echo "  URL Path:      $URL_PATH"
echo "  Client ID:     $CLIENT_ID"
echo "  Client Secret: ${CLIENT_SECRET:0:4}****${CLIENT_SECRET: -4}"
echo "  Scope:         ${SCOPE:-<empty>}"
echo "  Audience:      ${AUDIENCE:-<not set>}"
echo ""

# Define endpoints to try (same order as oauth.py)
if [[ -n "$SPECIFIC_ENDPOINT" ]]; then
    ENDPOINTS=("${BASE_URL}${SPECIFIC_ENDPOINT}")
else
    ENDPOINTS=(
        "${BASE_URL}/identity/connect/token"                    # MSI On-Premise
        "${BASE_URL}${URL_PATH}/identity/connect/token"         # MSI On-Premise with path
        "${BASE_URL}/identity_/connect/token"                   # Cloud & Automation Suite
    )
fi

# Function to test an endpoint
test_endpoint() {
    local endpoint="$1"
    local attempt="$2"
    local total="$3"
    
    echo "------------------------------------------------------------------------"
    print_info "Attempt $attempt/$total: Testing endpoint"
    echo "  URL: $endpoint"
    echo ""
    
    # Build form data
    local form_data="grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}"
    
    # Add scope if provided (empty by default to match oauth.py)
    form_data="${form_data}&scope=${SCOPE}"
    
    # Add audience if provided
    if [[ -n "$AUDIENCE" ]]; then
        form_data="${form_data}&audience=${AUDIENCE}"
    fi
    
    # Show curl command if verbose
    if [[ $VERBOSE -eq 1 ]]; then
        print_info "Curl command:"
        echo "curl -k -X POST \\"
        echo "  -H 'Content-Type: application/x-www-form-urlencoded' \\"
        echo "  -d 'grant_type=client_credentials' \\"
        echo "  -d 'client_id=${CLIENT_ID}' \\"
        echo "  -d 'client_secret=****' \\"
        echo "  -d 'scope=${SCOPE}' \\"
        [[ -n "$AUDIENCE" ]] && echo "  -d 'audience=${AUDIENCE}' \\"
        echo "  '${endpoint}'"
        echo ""
    fi
    
    # Make the request
    print_info "Sending request..."
    
    response=$(curl -k -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "$form_data" \
        "$endpoint" 2>&1)
    
    # Extract HTTP status code (last line)
    http_code=$(echo "$response" | tail -n1)
    # Extract response body (all but last line)
    response_body=$(echo "$response" | sed '$d')
    
    echo ""
    print_info "Response:"
    echo "  HTTP Status: $http_code"
    
    if [[ "$http_code" == "200" ]]; then
        # Success!
        print_success "SUCCESS! Token obtained"
        echo ""
        echo "Response Body:"
        echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
        echo ""
        
        # Extract and display key information
        access_token=$(echo "$response_body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
        token_type=$(echo "$response_body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token_type', 'N/A'))" 2>/dev/null)
        expires_in=$(echo "$response_body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('expires_in', 'N/A'))" 2>/dev/null)
        
        if [[ -n "$access_token" ]]; then
            echo "========================================================================"
            print_success "OAuth Token Details:"
            echo "  Access Token: ${access_token:0:50}..."
            echo "  Token Type:   $token_type"
            echo "  Expires In:   $expires_in seconds"
            echo "========================================================================"
            return 0
        else
            print_error "No access_token in response!"
            return 1
        fi
    else
        # Failed
        print_error "Request failed with HTTP $http_code"
        echo ""
        echo "Response Body:"
        echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
        echo ""
        return 1
    fi
}

# Try each endpoint
total_endpoints=${#ENDPOINTS[@]}
attempt=1
success=0

for endpoint in "${ENDPOINTS[@]}"; do
    if test_endpoint "$endpoint" "$attempt" "$total_endpoints"; then
        success=1
        break
    fi
    attempt=$((attempt + 1))
    
    if [[ $attempt -le $total_endpoints ]]; then
        print_warning "Trying next endpoint..."
        echo ""
    fi
done

echo ""
echo "========================================================================"
if [[ $success -eq 1 ]]; then
    print_success "✅ OAuth credentials are VALID and working!"
    echo "========================================================================"
    exit 0
else
    print_error "❌ All endpoints failed. OAuth credentials may be invalid."
    echo ""
    echo "Possible issues:"
    echo "  1. Invalid client_id or client_secret"
    echo "  2. OAuth application not configured in UiPath"
    echo "  3. Incorrect UiPath URL"
    echo "  4. Network connectivity issues"
    echo "  5. Identity server endpoint not accessible"
    echo "========================================================================"
    exit 1
fi
