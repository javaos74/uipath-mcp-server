"""MCP Client for communicating with MCP servers via SSE"""
import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Callable, Awaitable

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp import types

logger = logging.getLogger(__name__)


class Tool:
    """Represents a tool with its properties"""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        title: Optional[str] = None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.input_schema = input_schema

    def format_for_llm(self) -> str:
        """Format tool information for LLM"""
        args_desc = []
        if "properties" in self.input_schema:
            for param_name, param_info in self.input_schema["properties"].items():
                arg_desc = f"- {param_name}: {param_info.get('description', 'No description')}"
                if param_name in self.input_schema.get("required", []):
                    arg_desc += " (required)"
                args_desc.append(arg_desc)

        output = f"Tool: {self.name}\n"
        if self.title:
            output += f"Title: {self.title}\n"
        output += f"Description: {self.description}\n"
        if args_desc:
            output += f"Arguments:\n{chr(10).join(args_desc)}\n"

        return output

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


class MCPServer:
    """Manages a single MCP server connection via SSE"""

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        logging_callback: Optional[Callable[[types.LoggingMessageNotificationParams], Awaitable[None]]] = None,
        message_handler: Optional[Callable[[Any], Awaitable[None]]] = None,
    ):
        self.name = name
        self.config = config
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._cleanup_lock = asyncio.Lock()
        self._logging_callback = logging_callback
        self._message_handler = message_handler

    async def initialize(self) -> None:
        """Initialize the SSE server connection"""
        url = self.config.get("url")
        if not url:
            raise ValueError(f"Server {self.name}: 'url' is required")

        headers = self.config.get("headers", {})
        timeout = self.config.get("timeout", 30)
        sse_read_timeout = self.config.get("sse_read_timeout", 300)

        # Create auth if token is provided
        auth = None
        if "token" in self.config and self.config["token"]:
            # Create a custom auth class for Bearer token
            class BearerAuth(httpx.Auth):
                def __init__(self, token: str):
                    self.token = token

                def auth_flow(self, request: httpx.Request):
                    request.headers["Authorization"] = f"Bearer {self.token}"
                    yield request

            auth = BearerAuth(self.config["token"])

        try:
            logger.info(f"Connecting to SSE server {self.name} at {url}")

            # Connect to SSE server
            sse_transport = await self.exit_stack.enter_async_context(
                sse_client(
                    url=url,
                    headers=headers,
                    timeout=timeout,
                    sse_read_timeout=sse_read_timeout,
                    auth=auth,
                )
            )

            read_stream, write_stream = sse_transport

            # Create and initialize session with notification handlers
            session = await self.exit_stack.enter_async_context(
                ClientSession(
                    read_stream,
                    write_stream,
                    logging_callback=self._logging_callback,
                    message_handler=self._message_handler,
                )
            )

            await session.initialize()
            self.session = session

            logger.info(f"Successfully initialized MCP server: {self.name}")
        except Exception as e:
            logger.error(f"Error initializing server {self.name}: {e}")
            await self.cleanup()
            raise

    async def list_tools(self) -> List[Tool]:
        """List available tools from the server"""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        try:
            tools_response = await self.session.list_tools()
            tools = []

            # Handle the response structure
            if hasattr(tools_response, "tools"):
                for tool in tools_response.tools:
                    tools.append(
                        Tool(
                            tool.name,
                            tool.description,
                            tool.inputSchema,
                            getattr(tool, "title", None),
                        )
                    )

            return tools
        except Exception as e:
            logger.error(f"Error listing tools from {self.name}: {e}")
            return []

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        retries: int = 2,
        delay: float = 1.0,
    ) -> Any:
        """Execute a tool with retry mechanism"""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        attempt = 0
        while attempt < retries:
            try:
                logger.info(f"Executing {tool_name} on {self.name}...")
                result = await self.session.call_tool(tool_name, arguments)

                # Extract content from result
                if hasattr(result, "content"):
                    content_list = []
                    for content in result.content:
                        if hasattr(content, "type"):
                            if content.type == "text":
                                content_list.append(content.text)
                            else:
                                content_list.append(str(content))
                        else:
                            content_list.append(str(content))
                    return {"content": content_list}

                return result
            except Exception as e:
                attempt += 1
                logger.warning(
                    f"Error executing tool: {e}. Attempt {attempt} of {retries}"
                )
                if attempt < retries:
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached")
                    raise

    async def cleanup(self) -> None:
        """Clean up server resources"""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
                logger.info(f"Cleaned up server: {self.name}")
            except Exception as e:
                logger.error(f"Error during cleanup of server {self.name}: {e}")


class MCPClientManager:
    """Manager for multiple MCP servers"""

    def __init__(
        self,
        logging_callback: Optional[Callable[[str, types.LoggingMessageNotificationParams], Awaitable[None]]] = None,
        message_handler: Optional[Callable[[str, Any], Awaitable[None]]] = None,
    ):
        self.servers: Dict[str, MCPServer] = {}
        self._logging_callback = logging_callback
        self._message_handler = message_handler

    async def _default_logging_callback(
        self, server_name: str, params: types.LoggingMessageNotificationParams
    ) -> None:
        """Default logging callback that logs to Python logger"""
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        level = level_map.get(params.level, logging.INFO)
        logger.log(level, f"[{server_name}] {params.data}")

    async def _default_message_handler(self, server_name: str, message: Any) -> None:
        """Default message handler that logs notifications"""
        if isinstance(message, types.ServerNotification):
            logger.debug(f"[{server_name}] Received notification: {type(message.root).__name__}")
        elif isinstance(message, Exception):
            logger.error(f"[{server_name}] Received exception: {message}")

    async def add_server(self, name: str, config: Dict[str, Any]) -> None:
        """Add and initialize a new MCP server"""
        if not config.get("enabled", True):
            logger.info(f"Server {name} is disabled, skipping")
            return

        # Create server-specific callbacks that include server name
        async def logging_callback(params: types.LoggingMessageNotificationParams) -> None:
            if self._logging_callback:
                await self._logging_callback(name, params)
            else:
                await self._default_logging_callback(name, params)

        async def message_handler(message: Any) -> None:
            if self._message_handler:
                await self._message_handler(name, message)
            else:
                await self._default_message_handler(name, message)

        server = MCPServer(name, config, logging_callback, message_handler)
        try:
            await server.initialize()
            self.servers[name] = server
        except Exception as e:
            logger.error(f"Failed to add server {name}: {e}")
            raise

    async def remove_server(self, name: str) -> None:
        """Remove an MCP server"""
        if name in self.servers:
            await self.servers[name].cleanup()
            del self.servers[name]

    async def list_all_tools(self) -> Dict[str, List[Tool]]:
        """List tools from all connected servers"""
        all_tools = {}
        for name, server in self.servers.items():
            try:
                tools = await server.list_tools()
                all_tools[name] = tools
            except Exception as e:
                logger.error(f"Error listing tools from {name}: {e}")
                all_tools[name] = []
        return all_tools

    async def execute_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """Execute a tool on a specific server"""
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")

        server = self.servers[server_name]
        return await server.execute_tool(tool_name, arguments)

    async def cleanup_all(self) -> None:
        """Clean up all servers"""
        for server in reversed(list(self.servers.values())):
            try:
                await server.cleanup()
            except Exception as e:
                logger.warning(f"Warning during cleanup: {e}")
        self.servers.clear()
