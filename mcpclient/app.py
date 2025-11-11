"""Chainlit MCP Client Application"""
import chainlit as cl
from openai import AsyncOpenAI
import json
from typing import List, Dict, Any, Optional
import logging
import asyncio

from config import config
from mcp_client import MCPClientManager, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global MCP manager
mcp_manager: Optional[MCPClientManager] = None


async def logging_notification_handler(server_name: str, params) -> None:
    """Handle logging notifications from MCP servers"""
    # Send log messages to Chainlit UI
    level_emoji = {
        "debug": "🔍",
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "critical": "🚨",
    }
    emoji = level_emoji.get(params.level, "📝")
    
    # Only show warning and above in UI
    if params.level in ["warning", "error", "critical"]:
        await cl.Message(
            content=f"{emoji} **[{server_name}]** {params.data}",
            author=server_name,
        ).send()
    
    # Always log to Python logger
    logger.info(f"[{server_name}] {params.level}: {params.data}")


async def message_notification_handler(server_name: str, message: Any) -> None:
    """Handle general notifications from MCP servers"""
    from mcp import types
    
    if isinstance(message, types.ServerNotification):
        notification_type = type(message.root).__name__
        logger.debug(f"[{server_name}] Notification: {notification_type}")
        
        # Handle specific notification types
        if isinstance(message.root, types.ResourceUpdatedNotification):
            logger.info(f"[{server_name}] Resource updated: {message.root.params.uri}")
        elif isinstance(message.root, types.ResourceListChangedNotification):
            logger.info(f"[{server_name}] Resource list changed")
        elif isinstance(message.root, types.PromptListChangedNotification):
            logger.info(f"[{server_name}] Prompt list changed")
        elif isinstance(message.root, types.ToolListChangedNotification):
            logger.info(f"[{server_name}] Tool list changed")
    elif isinstance(message, Exception):
        logger.error(f"[{server_name}] Exception: {message}")


async def initialize_mcp_servers():
    """Initialize all MCP servers from config"""
    global mcp_manager
    
    if mcp_manager is None:
        mcp_manager = MCPClientManager(
            logging_callback=logging_notification_handler,
            message_handler=message_notification_handler,
        )
    
    # Initialize servers from config
    for server_name, server_config in config.mcpServers.items():
        try:
            await mcp_manager.add_server(server_name, server_config.model_dump())
            logger.info(f"Initialized server: {server_name}")
        except Exception as e:
            logger.error(f"Failed to initialize server {server_name}: {e}")


@cl.on_chat_start
async def start():
    """Initialize chat session"""
    
    # Check if this is first time setup
    if not config.openai_api_key:
        await show_settings_form()
        return
    
    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=config.openai_api_key)
    cl.user_session.set("client", client)
    
    # Initialize MCP servers
    init_msg = cl.Message(content="🔄 MCP 서버를 초기화하는 중...")
    await init_msg.send()
    
    try:
        await initialize_mcp_servers()
        
        # Get available tools
        all_tools = await mcp_manager.list_all_tools()
        total_tools = sum(len(tools) for tools in all_tools.values())
        
        if all_tools:
            init_msg.content = f"✅ MCP 서버 초기화 완료! {len(all_tools)}개 서버, {total_tools}개 도구 사용 가능"
        else:
            init_msg.content = "ℹ️ 연결된 MCP 서버가 없습니다. `/servers` 명령으로 서버를 추가하세요."
        await init_msg.update()
    except Exception as e:
        init_msg.content = f"⚠️ MCP 서버 초기화 중 일부 오류 발생. `/servers`로 서버를 확인하세요."
        await init_msg.update()
        logger.error(f"MCP initialization error: {e}")
    
    # Store message history
    cl.user_session.set("message_history", [])
    
    # Welcome message
    welcome_msg = """
# 🤖 MCP Client에 오신 것을 환영합니다!

이 클라이언트는 MCP (Model Context Protocol) 서버와 통신하며 OpenAI를 사용합니다.

## 사용 가능한 명령어:
- `/settings` - OpenAI API 키 설정
- `/servers` - MCP 서버 관리
- `/tools` - 사용 가능한 도구 목록 보기
- `/new` - 새 채팅 시작
- 일반 메시지 - AI와 대화하기

파일을 업로드하여 처리할 수도 있습니다.
"""
    await cl.Message(content=welcome_msg).send()


@cl.on_chat_end
async def end():
    """Clean up when chat ends"""
    global mcp_manager
    if mcp_manager:
        await mcp_manager.cleanup_all()
        logger.info("Cleaned up MCP servers")


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages"""
    
    # Handle commands
    if message.content.startswith("/"):
        await handle_command(message)
        return
    
    # Get OpenAI client
    client = cl.user_session.get("client")
    if not client:
        await cl.Message(
            content="❌ OpenAI 클라이언트가 초기화되지 않았습니다. API 키를 설정하고 재시작해주세요."
        ).send()
        return
    
    # Handle file uploads
    files_content = ""
    if message.elements:
        files_content = await process_uploaded_files(message.elements)
    
    # Get message history
    message_history = cl.user_session.get("message_history", [])
    
    # Add user message to history
    user_message = message.content
    if files_content:
        user_message += f"\n\n[업로드된 파일 내용]\n{files_content}"
    
    message_history.append({
        "role": "user",
        "content": user_message
    })
    
    # Get available tools
    all_tools = await mcp_manager.list_all_tools()
    tools_for_openai = []
    tool_map = {}  # Map tool name to (server_name, tool)
    
    for server_name, tools in all_tools.items():
        for tool in tools:
            tools_for_openai.append(tool.to_openai_format())
            tool_map[tool.name] = (server_name, tool)
    
    # Prepare messages for OpenAI
    messages = message_history.copy()
    
    # Stream response from OpenAI
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        # Call OpenAI with function calling
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools_for_openai if tools_for_openai else None,
            tool_choice="auto" if tools_for_openai else None,
            temperature=0.7,
            stream=True
        )
        
        full_response = ""
        tool_calls = []
        current_tool_call = None
        
        async for chunk in response:
            delta = chunk.choices[0].delta
            
            # Handle content
            if delta.content:
                full_response += delta.content
                await msg.stream_token(delta.content)
            
            # Handle tool calls
            if delta.tool_calls:
                for tc_chunk in delta.tool_calls:
                    if tc_chunk.index is not None:
                        # New tool call or continuing existing one
                        while len(tool_calls) <= tc_chunk.index:
                            tool_calls.append({
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            })
                        
                        if tc_chunk.id:
                            tool_calls[tc_chunk.index]["id"] = tc_chunk.id
                        
                        if tc_chunk.function:
                            if tc_chunk.function.name:
                                tool_calls[tc_chunk.index]["function"]["name"] = tc_chunk.function.name
                            if tc_chunk.function.arguments:
                                tool_calls[tc_chunk.index]["function"]["arguments"] += tc_chunk.function.arguments
        
        # If no content was streamed, update the message
        if not full_response and not tool_calls:
            await msg.update()
        elif full_response:
            await msg.update()
        
        # Handle tool calls
        if tool_calls:
            # Add assistant message with tool calls to history
            message_history.append({
                "role": "assistant",
                "content": full_response if full_response else None,
                "tool_calls": tool_calls
            })
            
            # Execute tools
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                
                if tool_name in tool_map:
                    server_name, tool = tool_map[tool_name]
                    
                    # Show tool execution message
                    tool_msg = cl.Message(
                        content=f"🔧 도구 실행 중: `{tool_name}` (서버: {server_name})"
                    )
                    await tool_msg.send()
                    
                    try:
                        result = await mcp_manager.execute_tool(
                            server_name,
                            tool_name,
                            tool_args
                        )
                        
                        result_str = json.dumps(result, ensure_ascii=False, indent=2)
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result_str
                        })
                        
                        tool_msg.content = f"✅ 도구 실행 완료: `{tool_name}`\n```json\n{result_str}\n```"
                        await tool_msg.update()
                    except Exception as e:
                        error_msg = f"도구 실행 오류: {str(e)}"
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": error_msg
                        })
                        tool_msg.content = f"❌ {error_msg}"
                        await tool_msg.update()
            
            # Add tool results to history
            message_history.extend(tool_results)
            
            # Get final response from OpenAI
            final_msg = cl.Message(content="")
            await final_msg.send()
            
            final_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=message_history,
                temperature=0.7,
                stream=True
            )
            
            final_content = ""
            async for chunk in final_response:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    final_content += token
                    await final_msg.stream_token(token)
            
            await final_msg.update()
            
            # Add final response to history
            message_history.append({
                "role": "assistant",
                "content": final_content
            })
        else:
            # No tool calls, just add the response to history
            message_history.append({
                "role": "assistant",
                "content": full_response
            })
        
        cl.user_session.set("message_history", message_history)
        
    except Exception as e:
        logger.error(f"Error in chat completion: {e}")
        await cl.Message(content=f"❌ 오류가 발생했습니다: {str(e)}").send()


async def handle_command(message: cl.Message):
    """Handle special commands"""
    command = message.content.lower().strip()
    
    if command == "/settings":
        await show_settings_form()
    elif command == "/servers":
        await show_mcp_servers_list()
    elif command == "/tools":
        await show_tools()
    elif command == "/new":
        await start_new_chat()
    else:
        await cl.Message(content=f"❌ 알 수 없는 명령어: {command}").send()


async def show_settings_form():
    """Show interactive settings form"""
    settings = cl.ChatSettings(
        [
            cl.input_widget.TextInput(
                id="openai_api_key",
                label="OpenAI API Key",
                initial=config.openai_api_key if config.openai_api_key else "",
                placeholder="sk-...",
                description="OpenAI API 키를 입력하세요",
            ),
        ]
    )
    await settings.send()
    
    # Show current MCP servers
    await show_mcp_servers_list()


async def show_mcp_servers_list():
    """Show list of MCP servers with management actions"""
    servers_text = "# 🔌 MCP 서버 관리\n\n"
    
    if config.mcpServers:
        for server_name, server_config in config.mcpServers.items():
            status = "✅" if server_config.enabled else "❌"
            servers_text += f"## {status} {server_name}\n"
            servers_text += f"- URL: `{server_config.url}`\n"
            servers_text += f"- Token: {'설정됨' if server_config.token else '미설정'}\n"
            servers_text += f"- Timeout: {server_config.timeout}초\n\n"
    else:
        servers_text += "등록된 서버가 없습니다.\n\n"
    
    servers_text += "아래 버튼을 사용하여 서버를 관리하세요."
    
    actions = [
        cl.Action(
            name="add_server",
            value="add_server",
            payload={"action": "add_server"},
            label="➕ 서버 추가",
        ),
        cl.Action(
            name="refresh_servers",
            value="refresh",
            payload={"action": "refresh"},
            label="🔄 새로고침",
        ),
    ]
    
    await cl.Message(content=servers_text, actions=actions).send()


async def show_settings():
    """Show settings dialog"""
    await show_settings_form()


@cl.on_settings_update
async def on_settings_update(settings: Dict[str, Any]):
    """Handle settings update"""
    logger.info(f"Settings updated: {settings}")
    
    # Update OpenAI API key
    if "openai_api_key" in settings and settings["openai_api_key"]:
        config.openai_api_key = settings["openai_api_key"]
        config.save_to_file()
        
        # Reinitialize OpenAI client
        client = AsyncOpenAI(api_key=config.openai_api_key)
        cl.user_session.set("client", client)
        
        await cl.Message(content="✅ OpenAI API 키가 업데이트되었습니다!").send()
        
        # Initialize MCP servers if not already done
        if mcp_manager is None or not mcp_manager.servers:
            await initialize_mcp_servers()


@cl.action_callback("add_server")
async def on_add_server(action: cl.Action):
    """Handle add server action"""
    # Ask for server details
    res = await cl.AskUserMessage(
        content="새 MCP 서버의 이름을 입력하세요:",
        timeout=60,
    ).send()
    
    if not res:
        return
    
    server_name = res["output"].strip()
    if not server_name:
        await cl.Message(content="❌ 서버 이름이 필요합니다.").send()
        return
    
    # Ask for URL
    res = await cl.AskUserMessage(
        content=f"**{server_name}** 서버의 SSE 엔드포인트 URL을 입력하세요:\n예: http://localhost:8000/sse",
        timeout=60,
    ).send()
    
    if not res:
        return
    
    server_url = res["output"].strip()
    if not server_url:
        await cl.Message(content="❌ URL이 필요합니다.").send()
        return
    
    # Ask for token (optional)
    res = await cl.AskUserMessage(
        content="Bearer 토큰을 입력하세요 (선택사항, 없으면 Enter):",
        timeout=60,
    ).send()
    
    server_token = res["output"].strip() if res and res["output"] else None
    
    # Add server to config
    from config import MCPServerConfig
    
    config.mcpServers[server_name] = MCPServerConfig(
        url=server_url,
        token=server_token if server_token else None,
        enabled=True,
    )
    config.save_to_file()
    
    await cl.Message(content=f"✅ 서버 **{server_name}**이(가) 추가되었습니다!").send()
    
    # Try to initialize the server
    try:
        await mcp_manager.add_server(server_name, config.mcpServers[server_name].model_dump())
        await cl.Message(content=f"✅ 서버 **{server_name}** 연결 성공!").send()
    except Exception as e:
        await cl.Message(content=f"⚠️ 서버 연결 실패: {str(e)}\n설정은 저장되었습니다.").send()
    
    # Refresh server list
    await show_mcp_servers_list()


@cl.action_callback("refresh_servers")
async def on_refresh_servers(action: cl.Action):
    """Handle refresh servers action"""
    await show_mcp_servers_list()


async def show_tools():
    """Show available tools from all MCP servers"""
    msg = cl.Message(content="🔍 도구 목록을 가져오는 중...")
    await msg.send()
    
    all_tools = await mcp_manager.list_all_tools()
    
    if not all_tools:
        msg.content = "❌ 연결된 MCP 서버가 없거나 도구를 가져올 수 없습니다."
        await msg.update()
        return
    
    tools_text = "# 🛠️ 사용 가능한 도구\n\n"
    
    for server_name, tools in all_tools.items():
        tools_text += f"## 서버: {server_name}\n\n"
        if tools:
            for tool in tools:
                tools_text += f"### {tool.name}\n"
                if tool.title:
                    tools_text += f"**{tool.title}**\n\n"
                tools_text += f"{tool.description}\n\n"
                
                if "properties" in tool.input_schema:
                    tools_text += "**매개변수:**\n"
                    for param_name, param_info in tool.input_schema["properties"].items():
                        required = " (필수)" if param_name in tool.input_schema.get("required", []) else ""
                        tools_text += f"- `{param_name}`: {param_info.get('description', 'No description')}{required}\n"
                    tools_text += "\n"
        else:
            tools_text += "도구가 없습니다.\n\n"
    
    msg.content = tools_text
    await msg.update()


async def start_new_chat():
    """Start a new chat session"""
    cl.user_session.set("message_history", [])
    await cl.Message(content="✨ 새로운 채팅을 시작합니다!").send()


async def process_uploaded_files(elements: List[Any]) -> str:
    """Process uploaded files"""
    files_content = []
    
    for element in elements:
        # Check if it's a file-like element
        if hasattr(element, 'path') and hasattr(element, 'name'):
            try:
                # Read file content
                with open(element.path, "r", encoding="utf-8") as f:
                    content = f.read()
                files_content.append(f"파일명: {element.name}\n내용:\n{content}\n")
            except UnicodeDecodeError:
                # Try binary file
                try:
                    with open(element.path, "rb") as f:
                        content = f.read()
                    files_content.append(f"파일명: {element.name}\n(바이너리 파일, {len(content)} bytes)\n")
                except Exception as e:
                    files_content.append(f"파일명: {element.name}\n오류: {str(e)}\n")
            except Exception as e:
                files_content.append(f"파일명: {element.name}\n오류: {str(e)}\n")
    
    return "\n---\n".join(files_content)


if __name__ == "__main__":
    # This is handled by chainlit CLI
    pass
