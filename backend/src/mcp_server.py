"""MCP Server that dynamically exposes registered tools."""

from mcp.server import Server
from mcp.types import Tool, TextContent
import json
import asyncio
import logging
from typing import Optional

from .database import Database
from .uipath_client import UiPathClient

# Configure logging
logger = logging.getLogger(__name__)


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
            """Handle tool calls with background progress monitoring."""

            # Get tool from database
            tool = await self.db.get_tool(self.server_id, name)

            if not tool:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"success": False, "error": f"Tool '{name}' not found"}
                        ),
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

                    # Execute process
                    job = await self.uipath_client.execute_process(
                        process_name=tool["uipath_process_name"],
                        folder_path=tool["uipath_folder_path"] or "",
                        input_arguments=arguments,
                        uipath_url=uipath_url,
                        uipath_access_token=uipath_token,
                        folder_id=tool.get("uipath_folder_id"),
                    )

                    job_id = job.get("id", "")
                    folder_id = job.get("folder_id", "") or tool.get("uipath_folder_id")
                    progress_token = f"uipath_job_{job_id}"

                    # Capture current session for background notifications
                    session = self.server.request_context.session

                    # Background task for monitoring and progress notifications
                    async def monitor_job_with_progress():
                        """Monitor job and send progress notifications."""
                        try:
                            logger.info(
                                f"Starting job monitoring for job_id={job_id}, process={tool['uipath_process_name']}"
                            )

                            # Initial progress
                            await session.send_progress_notification(
                                progress_token=progress_token, progress=10, total=100
                            )

                            poll_count = 0
                            max_polls = 150  # 5 minutes with 2 second intervals

                            while poll_count < max_polls:
                                await asyncio.sleep(2)
                                poll_count += 1

                                # Get job status
                                status = await self.uipath_client.get_job_status(
                                    job_id=job_id,
                                    uipath_url=uipath_url,
                                    uipath_access_token=uipath_token,
                                    folder_id=folder_id,
                                )

                                state = status.get("state", "").lower()
                                logger.info(
                                    f"Job {job_id} status check #{poll_count}: state={state}, info={status.get('info', 'N/A')}"
                                )

                                # Check if job completed
                                if state == "successful":
                                    logger.info(f"Job {job_id} completed successfully")
                                    # Send final progress
                                    await session.send_progress_notification(
                                        progress_token=progress_token,
                                        progress=100,
                                        total=100,
                                    )
                                    # Return success result
                                    output_args = status.get("output_arguments")
                                    logger.info(f"Job {job_id} output: {output_args}")
                                    return {
                                        "success": True,
                                        "job_id": job_id,
                                        "status": "successful",
                                        "message": f"Process '{tool['uipath_process_name']}' completed successfully",
                                        "output": output_args if output_args else {},
                                    }

                                elif state == "faulted":
                                    logger.error(
                                        f"Job {job_id} faulted: {status.get('info', 'No error info')}"
                                    )
                                    # Send final progress
                                    await session.send_progress_notification(
                                        progress_token=progress_token,
                                        progress=90,
                                        total=100,
                                    )
                                    # Return failure result
                                    return {
                                        "success": False,
                                        "job_id": job_id,
                                        "status": "faulted",
                                        "error": f"Process '{tool['uipath_process_name']}' failed",
                                        "info": status.get("info", ""),
                                    }

                                elif state == "stopped":
                                    logger.warning(f"Job {job_id} was stopped")
                                    # Send final progress
                                    await session.send_progress_notification(
                                        progress_token=progress_token,
                                        progress=90,
                                        total=100,
                                    )
                                    # Return stopped result
                                    return {
                                        "success": False,
                                        "job_id": job_id,
                                        "status": "stopped",
                                        "message": f"Process '{tool['uipath_process_name']}' was stopped",
                                        "info": status.get("info", ""),
                                    }

                                else:
                                    # Send incremental progress
                                    progress = min(
                                        10 + (poll_count * 80 // max_polls), 90
                                    )
                                    await session.send_progress_notification(
                                        progress_token=progress_token,
                                        progress=progress,
                                        total=100,
                                    )

                            # Timeout
                            logger.warning(
                                f"Job {job_id} timed out after {max_polls * 2} seconds"
                            )
                            return {
                                "success": False,
                                "job_id": job_id,
                                "status": "timeout",
                                "error": f"Process '{tool['uipath_process_name']}' timed out after 5 minutes",
                                "message": "Job may still be running. Check UiPath Orchestrator for status.",
                            }

                        except Exception as e:
                            logger.error(
                                f"Error monitoring job {job_id}: {e}", exc_info=True
                            )
                            return {
                                "success": False,
                                "job_id": job_id,
                                "status": "error",
                                "error": f"Error monitoring job: {str(e)}",
                            }

                    # Create and await the monitoring task
                    task = asyncio.create_task(monitor_job_with_progress())
                    result = await task

                    # Return the result
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                except Exception as e:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": False,
                                    "error": f"Error executing process: {str(e)}",
                                },
                                indent=2,
                            ),
                        )
                    ]
            else:
                # Tool without UiPath process - return the arguments as confirmation
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": f"Tool '{name}' called successfully",
                                "arguments": arguments,
                                "note": "No UiPath process configured for this tool",
                            },
                            indent=2,
                        ),
                    )
                ]

    async def initialize(self):
        """Initialize server (placeholder for future use)."""
        pass

    def get_server(self) -> Server:
        """Get the MCP server instance."""
        return self.server
