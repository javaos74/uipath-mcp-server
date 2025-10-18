"""MCP Server that dynamically exposes registered tools."""

from mcp.server import Server
from mcp.types import Tool, TextContent
import json
from typing import Optional

from .database import Database
from .uipath_client import UiPathClient


class DynamicMCPServer:
    """Dynamic MCP Server that exposes registered tools from database."""

    def __init__(self, server_id: int, db: Database, user_id: Optional[int] = None):
        """Initialize the MCP server.
        
        Args:
            server_id: Database ID of the MCP server
            db: Database instance
            user_id: User ID for UiPath credentials (optional)
        """
        self.server_id = server_id
        self.db = db
        self.user_id = user_id
        self.uipath_client = UiPathClient()
        self.server = Server(f"uipath-mcp-server-{server_id}")
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP server handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools from database."""
            tools_data = await self.db.list_tools(self.server_id)
            
            tools = []
            for tool_data in tools_data:
                tools.append(
                    Tool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        inputSchema=tool_data["input_schema"],
                    )
                )
            
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls."""
            
            # Get tool from database
            tool = await self.db.get_tool(self.server_id, name)
            
            if not tool:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"Tool '{name}' not found"
                        })
                    )
                ]
            
            # If tool has UiPath process configured, execute it
            if tool["uipath_process_name"]:
                try:
                    # Get user's UiPath credentials if user_id is set
                    uipath_url = None
                    uipath_token = None
                    
                    if self.user_id:
                        user = await self.db.get_user_by_id(self.user_id)
                        if user:
                            uipath_url = user.get("uipath_url")
                            uipath_token = user.get("uipath_access_token")
                    
                    job = await self.uipath_client.execute_process(
                        process_name=tool["uipath_process_name"],
                        folder_path=tool["uipath_folder_path"] or "",
                        input_arguments=arguments,
                        uipath_url=uipath_url,
                        uipath_access_token=uipath_token
                    )
                    
                    result = {
                        "success": True,
                        "job_id": job.get("id", ""),
                        "status": job.get("state", "Unknown"),
                        "message": f"Process '{tool['uipath_process_name']}' started successfully",
                        "info": job.get("info", "")
                    }
                    return [TextContent(type="text", text=json.dumps(result))]
                
                except Exception as e:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": False,
                                "error": f"Error executing process: {str(e)}"
                            })
                        )
                    ]
            else:
                # Tool without UiPath process - return the arguments as confirmation
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "message": f"Tool '{name}' called successfully",
                            "arguments": arguments,
                            "note": "No UiPath process configured for this tool"
                        })
                    )
                ]

    async def initialize(self):
        """Initialize server (placeholder for future use)."""
        pass

    def get_server(self) -> Server:
        """Get the MCP server instance."""
        return self.server
