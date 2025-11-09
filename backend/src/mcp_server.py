"""MCP Server that dynamically exposes registered tools."""

from mcp.server import Server
from mcp.types import Tool, TextContent, LoggingLevel
import json
import asyncio
import logging
import os
from typing import Optional

from .database import Database
from .uipath_client import UiPathClient
from .oauth import exchange_client_credentials_for_token

# Configure logging
logger = logging.getLogger(__name__)

# Get tool call timeout from environment variable (default: 10 minutes = 600 seconds)
TOOL_CALL_TIMEOUT = int(os.getenv("TOOL_CALL_TIMEOUT", "600"))


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

        logger.info(
            f"Initializing MCP server {server_id} with tool call timeout: {TOOL_CALL_TIMEOUT}s ({TOOL_CALL_TIMEOUT // 60} minutes)"
        )

        self._setup_handlers()

    async def send_notification_message(
        self,
        session,
        message: str,
        level: LoggingLevel = "info",
        related_request_id: Optional[str] = None,
    ):
        """Send a log message notification to the client.

        This uses the MCP protocol's logging/message notification to send
        real-time status updates to the client during long-running operations.

        Args:
            session: MCP ServerSession object
            message: Message to send to the client
            level: Logging level ("debug", "info", "notice", "warning", "error", "critical", "alert", "emergency")
            related_request_id: Optional request ID to associate this log with
        """
        try:
            await session.send_log_message(
                level=level,
                data=message,
                logger="uipath-mcp-server",
                related_request_id=related_request_id,
            )
            logger.debug(f"Sent notification to client: [{level}] {message}")
        except Exception as e:
            logger.error(f"Failed to send notification message: {e}", exc_info=True)

    def _setup_handlers(self):
        """Setup MCP server handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools from database."""
            logger.info(f"=== list_tools invoked for server_id={self.server_id} ===")
            tools_data = await self.db.list_tools(self.server_id)
            logger.info(f"Found {len(tools_data)} tools in database")

            tools = []
            for tool_data in tools_data:
                tools.append(
                    Tool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        inputSchema=tool_data["input_schema"],
                    )
                )

            logger.info(f"Returning {len(tools)} tools")
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls with background progress monitoring."""

            logger.info(
                f"=== call_tool invoked: name={name}, arguments={arguments} ==="
            )

            # Get request context for progress notifications
            ctx = self.server.request_context
            progress_token = ctx.meta.progressToken if ctx.meta else None
            logger.info(f"Progress token from client: {progress_token}")

            # Get tool from database
            tool = await self.db.get_tool(self.server_id, name)
            logger.info(f"Tool retrieved from database: {tool}")

            if not tool:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"success": False, "error": f"Tool '{name}' not found"}
                        ),
                    )
                ]

            # Check tool type and execute accordingly
            tool_type = tool.get("tool_type", "uipath")
            
            if tool_type == "builtin":
                # Execute built-in tool
                logger.info(f"Executing built-in tool: {name}")
                try:
                    from .builtin.executor import execute_builtin_tool
                    
                    # Get built-in tool details
                    builtin_tool_id = tool.get("builtin_tool_id")
                    if not builtin_tool_id:
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps({
                                    "success": False,
                                    "error": "Built-in tool ID not found"
                                }),
                            )
                        ]
                    
                    builtin_tool = await self.db.get_builtin_tool(builtin_tool_id)
                    if not builtin_tool:
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps({
                                    "success": False,
                                    "error": f"Built-in tool with ID {builtin_tool_id} not found"
                                }),
                            )
                        ]
                    
                    # Get user's UiPath credentials if this is a UiPath tool
                    uipath_url = None
                    uipath_access_token = None
                    if "uipath_" in builtin_tool["python_function"]:
                        user_data = await self.db.get_user_by_id(self.user_id)
                        if user_data:
                            uipath_url = user_data.get("uipath_url")
                            uipath_access_token = user_data.get("uipath_access_token")
                            uipath_auth_type = user_data.get("uipath_auth_type", "pat")
                            
                            # Validate and refresh token if needed (OAuth only)
                            if uipath_auth_type == "oauth":
                                from .oauth import get_valid_token
                                
                                client_id = user_data.get("uipath_client_id")
                                client_secret = user_data.get("uipath_client_secret")
                                
                                if uipath_url and client_id and client_secret:
                                    try:
                                        # Get valid token (will refresh if expired)
                                        uipath_access_token = await get_valid_token(
                                            current_token=uipath_access_token,
                                            uipath_url=uipath_url,
                                            client_id=client_id,
                                            client_secret=client_secret,
                                        )
                                        
                                        # Update token in database if it changed
                                        if uipath_access_token != user_data.get("uipath_access_token"):
                                            await self.db.update_user_uipath_config(
                                                user_id=self.user_id,
                                                uipath_access_token=uipath_access_token,
                                            )
                                            logger.info(f"Refreshed OAuth token for user {self.user_id}")
                                    except Exception as e:
                                        logger.error(f"Failed to refresh OAuth token: {e}")
                                        # Continue with existing token, will fail if actually expired
                                else:
                                    logger.warning(f"OAuth mode but missing credentials for user {self.user_id}")
                            
                            logger.debug(f"Retrieved UiPath credentials for user {self.user_id}")
                    
                    # Execute the built-in tool
                    result = await execute_builtin_tool(
                        python_function=builtin_tool["python_function"],
                        arguments=arguments,
                        api_key=builtin_tool.get("api_key"),
                        uipath_url=uipath_url,
                        uipath_access_token=uipath_access_token
                    )
                    
                    logger.info(f"Built-in tool execution completed: {name}")
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(result, ensure_ascii=False, indent=2),
                        )
                    ]
                    
                except Exception as e:
                    logger.error(f"Error executing built-in tool: {e}", exc_info=True)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": False,
                                "error": "Built-in tool execution failed",
                                "message": str(e)
                            }),
                        )
                    ]
            
            # If tool has UiPath process configured, execute it
            elif tool["uipath_process_name"]:
                try:
                    # Get user's UiPath credentials if user_id is set
                    uipath_url = None
                    uipath_token = None
                    user_info = None

                    if self.user_id:
                        user = await self.db.get_user_by_id(self.user_id)
                        if user:
                            uipath_url = user.get("uipath_url")
                            user_info = user
                            
                            # Proactively ensure valid OAuth token
                            if user.get("uipath_auth_type") == "oauth":
                                from .oauth import get_valid_token
                                try:
                                    uipath_token = await get_valid_token(
                                        current_token=user.get("uipath_access_token"),
                                        uipath_url=uipath_url,
                                        client_id=user.get("uipath_client_id"),
                                        client_secret=user.get("uipath_client_secret"),
                                    )
                                    # Update DB if token was refreshed
                                    if uipath_token != user.get("uipath_access_token"):
                                        await self.db.update_user_uipath_config(
                                            user_id=self.user_id,
                                            uipath_access_token=uipath_token,
                                        )
                                        logger.info("Proactively refreshed OAuth token before process execution")
                                except Exception as token_err:
                                    logger.warning(f"Proactive token refresh failed: {token_err}")
                                    uipath_token = user.get("uipath_access_token")
                            else:
                                # PAT mode - use as-is
                                uipath_token = user.get("uipath_access_token")

                    # Execute process
                    logger.info(
                        f"Executing UiPath process: {tool['uipath_process_name']}"
                    )
                    try:
                        job = await self.uipath_client.execute_process(
                            process_name=tool["uipath_process_name"],
                            process_key=tool["uipath_process_key"],
                            folder_path=tool["uipath_folder_path"] or "",
                            input_arguments=arguments,
                            uipath_url=uipath_url,
                            uipath_access_token=uipath_token,
                            folder_id=tool.get("uipath_folder_id"),
                        )
                    except Exception as e:
                        msg = str(e)
                        is_unauthorized = (
                            "401" in msg or "403" in msg or "Unauthorized" in msg
                        )
                        can_refresh = (
                            user_info is not None
                            and user_info.get("uipath_auth_type") == "oauth"
                            and user_info.get("uipath_client_id")
                            and user_info.get("uipath_client_secret")
                            and (uipath_url or user_info.get("uipath_url"))
                        )
                        if is_unauthorized and can_refresh:
                            try:
                                logger.info("Attempting OAuth token refresh after 401/403...")
                                token_resp = await exchange_client_credentials_for_token(
                                    uipath_url=(uipath_url or user_info.get("uipath_url")),
                                    client_id=user_info.get("uipath_client_id"),
                                    client_secret=user_info.get("uipath_client_secret"),
                                )
                                new_token = token_resp.get("access_token")
                                if new_token:
                                    # Persist and retry once
                                    await self.db.update_user_uipath_config(
                                        user_id=user_info["id"],
                                        uipath_access_token=new_token,
                                    )
                                    uipath_token = new_token
                                    logger.info("Retrying process execution with refreshed token...")
                                    job = await self.uipath_client.execute_process(
                                        process_name=tool["uipath_process_name"],
                                        process_key=tool["uipath_process_key"],
                                        folder_path=tool["uipath_folder_path"] or "",
                                        input_arguments=arguments,
                                        uipath_url=uipath_url,
                                        uipath_access_token=uipath_token,
                                        folder_id=tool.get("uipath_folder_id"),
                                    )
                                else:
                                    raise RuntimeError("Token refresh did not return access_token")
                            except Exception as refresh_exc:
                                # If refresh fails, re-raise original error path
                                logger.error(f"Token refresh failed: {refresh_exc}", exc_info=True)
                                raise e
                        else:
                            # Not an auth error or cannot refresh
                            raise

                    job_id = job.get("id", "")
                    folder_id = job.get("folder_id", "") or tool.get("uipath_folder_id")

                    logger.info(f"UiPath job started: job_id={job_id}")

                    # Capture current session for background notifications
                    session = self.server.request_context.session
                    logger.info(f"Captured session: {session}")

                    # Background task for monitoring and progress notifications
                    async def monitor_job_with_progress(
                        session,
                        progress_token,
                        job_id: str,
                        folder_id: str,
                        tool_info: dict,
                        uipath_url: str,
                        uipath_token: str,
                        user_info: Optional[dict],
                        db: Database,
                    ):
                        """Monitor job and send progress notifications.

                        Args:
                            session: MCP server session for sending notifications
                            progress_token: Progress token from client (optional)
                            job_id: UiPath job ID to monitor
                            folder_id: UiPath folder ID
                            tool_info: Tool configuration dictionary
                            uipath_url: UiPath Orchestrator URL
                            uipath_token: UiPath access token
                        """
                        try:
                            logger.info(
                                f"Starting job monitoring for job_id={job_id}, process={tool_info['uipath_process_name']}"
                            )

                            # Send initial notification
                            await self.send_notification_message(
                                session,
                                f"🚀 Starting UiPath process '{tool_info['uipath_process_name']}' (Job ID: {job_id})",
                                "info",
                            )

                            # Send initial progress if token provided
                            if progress_token:
                                await session.send_progress_notification(
                                    progress_token=progress_token,
                                    progress=0,
                                    total=100,
                                    message=f"Starting process '{tool_info['uipath_process_name']}'",
                                )

                            poll_count = 0
                            poll_interval = 2  # seconds between each status check
                            max_polls = (
                                TOOL_CALL_TIMEOUT // poll_interval
                            )  # Calculate max polls based on timeout

                            logger.info(
                                f"Job monitoring timeout: {TOOL_CALL_TIMEOUT}s ({TOOL_CALL_TIMEOUT // 60} minutes)"
                            )

                            # Use a mutable token that can be refreshed in-loop
                            current_token = uipath_token

                            while poll_count < max_polls:
                                await asyncio.sleep(poll_interval)
                                poll_count += 1

                                # Get job status
                                try:
                                    status = await self.uipath_client.get_job_status(
                                        job_id=job_id,
                                        uipath_url=uipath_url,
                                        uipath_access_token=current_token,
                                        folder_id=folder_id,
                                    )
                                except Exception as status_exc:
                                    msg = str(status_exc)
                                    is_unauthorized = (
                                        "401" in msg or "403" in msg or "Unauthorized" in msg
                                    )
                                    can_refresh = (
                                        user_info is not None
                                        and user_info.get("uipath_auth_type") == "oauth"
                                        and user_info.get("uipath_client_id")
                                        and user_info.get("uipath_client_secret")
                                        and (uipath_url or user_info.get("uipath_url"))
                                    )
                                    if is_unauthorized and can_refresh:
                                        try:
                                            logger.info("Refreshing OAuth token during job monitoring (401/403)...")
                                            token_resp = await exchange_client_credentials_for_token(
                                                uipath_url=(uipath_url or user_info.get("uipath_url")),
                                                client_id=user_info.get("uipath_client_id"),
                                                client_secret=user_info.get("uipath_client_secret"),
                                            )
                                            new_token = token_resp.get("access_token")
                                            if new_token:
                                                await db.update_user_uipath_config(
                                                    user_id=user_info["id"],
                                                    uipath_access_token=new_token,
                                                )
                                                current_token = new_token
                                                # Retry once immediately
                                                status = await self.uipath_client.get_job_status(
                                                    job_id=job_id,
                                                    uipath_url=uipath_url,
                                                    uipath_access_token=current_token,
                                                    folder_id=folder_id,
                                                )
                                            else:
                                                raise RuntimeError("Token refresh did not return access_token")
                                        except Exception as refresh_exc:
                                            logger.error(
                                                f"Monitoring token refresh failed: {refresh_exc}",
                                                exc_info=True,
                                            )
                                            raise status_exc
                                    else:
                                        raise

                                state = status.get("state", "").lower()
                                info = status.get("info", "N/A")
                                logger.info(
                                    f"Job {job_id} status check #{poll_count}: state={state}, info={info}"
                                )

                                # Check if job completed
                                if state == "successful":
                                    logger.info(f"Job {job_id} completed successfully")

                                    # Send completion notification
                                    await self.send_notification_message(
                                        session,
                                        f"✅ Process '{tool_info['uipath_process_name']}' completed successfully",
                                        "info",
                                    )

                                    # Send final progress if token provided
                                    if progress_token:
                                        await session.send_progress_notification(
                                            progress_token=progress_token,
                                            progress=100,
                                            total=100,
                                            message="Process completed successfully",
                                        )

                                    # Return success result
                                    output_args = status.get("output_arguments")
                                    logger.info(f"Job {job_id} output: {output_args}")
                                    return {
                                        "success": True,
                                        "job_id": job_id,
                                        "status": "successful",
                                        "message": f"Process '{tool_info['uipath_process_name']}' completed successfully",
                                        "output": output_args if output_args else {},
                                    }

                                elif state == "faulted":
                                    error_msg = f"❌ Process '{tool_info['uipath_process_name']}' failed: {info}"
                                    logger.error(f"Job {job_id} faulted: {info}")

                                    # Send error notification
                                    await self.send_notification_message(
                                        session, error_msg, "error"
                                    )

                                    # Return failure result
                                    return {
                                        "success": False,
                                        "job_id": job_id,
                                        "status": "faulted",
                                        "error": f"Process '{tool_info['uipath_process_name']}' failed",
                                        "info": info,
                                    }

                                elif state == "stopped":
                                    logger.warning(f"Job {job_id} was stopped")

                                    # Send warning notification
                                    await self.send_notification_message(
                                        session,
                                        f"⚠️ Process '{tool_info['uipath_process_name']}' was stopped",
                                        "warning",
                                    )

                                    # Return stopped result
                                    return {
                                        "success": False,
                                        "job_id": job_id,
                                        "status": "stopped",
                                        "message": f"Process '{tool_info['uipath_process_name']}' was stopped",
                                        "info": info,
                                    }

                                else:
                                    # Calculate progress percentage
                                    progress_value = min(
                                        10 + (poll_count * 80 // max_polls), 90
                                    )
                                    elapsed_seconds = poll_count * poll_interval

                                    # Send progress update if token provided
                                    if progress_token:
                                        await session.send_progress_notification(
                                            progress_token=progress_token,
                                            progress=progress_value,
                                            total=100,
                                            message=f"작업상태: {state} (수행시간: {elapsed_seconds}초)",
                                        )

                            # Timeout
                            timeout_seconds = max_polls * poll_interval
                            timeout_minutes = timeout_seconds // 60
                            timeout_msg = f"Process '{tool_info['uipath_process_name']}' timed out after {timeout_minutes} minutes ({timeout_seconds}s)"
                            logger.warning(
                                f"Job {job_id} timed out after {timeout_seconds} seconds"
                            )

                            # Send timeout notification
                            await self.send_notification_message(
                                session,
                                f"{timeout_msg}. Job may still be running in UiPath Orchestrator.",
                                "warning",
                            )

                            return {
                                "success": False,
                                "job_id": job_id,
                                "status": "timeout",
                                "error": timeout_msg,
                                "message": "Job may still be running. Check UiPath Orchestrator for status.",
                            }

                        except Exception as e:
                            error_msg = f"Error monitoring job {job_id}: {str(e)}"
                            logger.error(error_msg, exc_info=True)

                            # Send error notification
                            try:
                                await self.send_notification_message(
                                    session, error_msg, "error"
                                )
                            except:
                                pass  # Don't fail if notification fails

                            return {
                                "success": False,
                                "job_id": job_id,
                                "status": "error",
                                "error": f"Error monitoring job: {str(e)}",
                            }

                    # Create and await the monitoring task
                    logger.info(f"Creating monitoring task for job {job_id}")
                    task = asyncio.create_task(
                        monitor_job_with_progress(
                            session=session,
                            progress_token=progress_token,
                            job_id=job_id,
                            folder_id=folder_id,
                            tool_info=tool,
                            uipath_url=uipath_url,
                            uipath_token=uipath_token,
                            user_info=user_info,
                            db=self.db,
                        )
                    )
                    logger.info(f"Waiting for monitoring task to complete...")
                    result = await task
                    logger.info(f"Monitoring task completed with result: {result}")

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
