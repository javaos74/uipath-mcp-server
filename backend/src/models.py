"""Pydantic models for API requests and responses."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr


# ==================== User Models ====================


class UserCreate(BaseModel):
    """Request model for creating a new user."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password")
    role: str = Field(default="user", description="User role (user or admin)")


class UserLogin(BaseModel):
    """Request model for user login."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    """Response model for user data."""

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    uipath_url: Optional[str] = None
    uipath_auth_type: Optional[str] = "pat"
    uipath_client_id: Optional[str] = None
    has_uipath_token: bool = False
    has_oauth_credentials: bool = False
    created_at: str
    updated_at: str


class UserInDB(UserResponse):
    """User model with hashed password and sensitive data (for internal use)."""

    hashed_password: str
    uipath_access_token: Optional[str] = None


class UiPathConfigUpdate(BaseModel):
    """Request model for updating UiPath configuration."""

    uipath_url: Optional[str] = Field(
        None,
        description="UiPath Cloud URL (e.g., https://cloud.uipath.com/account/tenant)",
    )
    uipath_auth_type: Optional[str] = Field(
        None, description="Authentication type: 'pat' or 'oauth'"
    )
    uipath_access_token: Optional[str] = Field(
        None, description="UiPath Personal Access Token (PAT)"
    )
    uipath_client_id: Optional[str] = Field(
        None, description="OAuth Client ID for UiPath authentication"
    )
    uipath_client_secret: Optional[str] = Field(
        None, description="OAuth Client Secret for UiPath authentication"
    )


class Token(BaseModel):
    """Response model for authentication token."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==================== MCP Server Models ====================


class ServerCreate(BaseModel):
    """Request model for creating a new MCP server endpoint."""

    tenant_name: str = Field(..., description="Tenant name for the endpoint")
    server_name: str = Field(..., description="Server name for the endpoint")
    description: Optional[str] = Field(None, description="Server description")


class ServerUpdate(BaseModel):
    """Request model for updating an MCP server."""

    description: Optional[str] = Field(None, description="Server description")


class ServerResponse(BaseModel):
    """Response model for MCP server data."""

    id: int
    tenant_name: str
    server_name: str
    description: Optional[str]
    user_id: int
    created_at: str
    updated_at: str


# ==================== MCP Tool Models ====================


class ToolCreate(BaseModel):
    """Request model for creating a new MCP tool.

    Follows MCP Tool specification:
    https://spec.modelcontextprotocol.io/specification/server/tools/
    """

    name: str = Field(..., description="Tool name (must be unique within server)")
    description: str = Field(..., description="Tool description")
    input_schema: Dict[str, Any] = Field(
        ...,
        description="JSON Schema for tool input (MCP Tool spec)",
        examples=[
            {
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First parameter"},
                    "param2": {"type": "number", "description": "Second parameter"},
                },
                "required": ["param1"],
            }
        ],
    )
    tool_type: str = Field(
        default="uipath", description="Tool type: 'uipath' or 'builtin'"
    )
    uipath_process_name: Optional[str] = Field(
        None, description="UiPath process name to execute (optional)"
    )
    uipath_process_key: Optional[str] = Field(
        None, description="UiPath process key (optional)"
    )
    uipath_folder_path: Optional[str] = Field(
        None, description="UiPath folder path (optional)"
    )
    uipath_folder_id: Optional[str] = Field(
        None, description="UiPath folder ID (optional)"
    )
    builtin_tool_id: Optional[int] = Field(
        None, description="Built-in tool ID (for builtin type)"
    )


class ToolUpdate(BaseModel):
    """Request model for updating an MCP tool."""

    description: Optional[str] = Field(None, description="Tool description")
    input_schema: Optional[Dict[str, Any]] = Field(
        None, description="JSON Schema for tool input"
    )
    tool_type: Optional[str] = Field(None, description="Tool type")
    uipath_process_name: Optional[str] = Field(None, description="UiPath process name")
    uipath_process_key: Optional[str] = Field(None, description="UiPath process key")
    uipath_folder_path: Optional[str] = Field(None, description="UiPath folder path")
    uipath_folder_id: Optional[str] = Field(None, description="UiPath folder ID")
    builtin_tool_id: Optional[int] = Field(None, description="Built-in tool ID")


class ToolResponse(BaseModel):
    """Response model for MCP tool data."""

    id: int
    server_id: int
    name: str
    description: str
    input_schema: Dict[str, Any]
    tool_type: str = "uipath"
    uipath_process_name: Optional[str]
    uipath_process_key: Optional[str]
    uipath_folder_path: Optional[str]
    uipath_folder_id: Optional[str]
    builtin_tool_id: Optional[int]
    created_at: str
    updated_at: str


# ==================== Tool Execution Models ====================


class ToolExecute(BaseModel):
    """Request model for executing a tool."""

    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Arguments for tool execution"
    )


class ToolExecuteResponse(BaseModel):
    """Response model for tool execution."""

    success: bool
    job_id: Optional[str] = None
    status: Optional[str] = None
    message: str
    result: Optional[Any] = None


# ==================== Built-in Tool Models ====================


class BuiltinToolCreate(BaseModel):
    """Request model for creating a new built-in tool."""

    name: str = Field(..., description="Tool name (must be unique)")
    description: str = Field(..., description="Tool description")
    input_schema: Dict[str, Any] = Field(
        ..., description="JSON Schema for tool input"
    )
    python_function: str = Field(
        ..., description="Python function name or module path"
    )
    api_key: Optional[str] = Field(None, description="API key for external service")


class BuiltinToolUpdate(BaseModel):
    """Request model for updating a built-in tool."""

    description: Optional[str] = Field(None, description="Tool description")
    input_schema: Optional[Dict[str, Any]] = Field(
        None, description="JSON Schema for tool input"
    )
    python_function: Optional[str] = Field(
        None, description="Python function name or module path"
    )
    api_key: Optional[str] = Field(None, description="API key for external service")
    is_active: Optional[bool] = Field(None, description="Active status")


class BuiltinToolResponse(BaseModel):
    """Response model for built-in tool data."""

    id: int
    name: str
    description: str
    input_schema: Dict[str, Any]
    python_function: str
    api_key: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
