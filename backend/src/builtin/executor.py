"""Built-in tool executor."""

import logging
import importlib
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# External package prefix
EXTERNAL_PACKAGE_PREFIX = "mcp_builtin_"


async def execute_builtin_tool(
    python_function: str,
    arguments: Dict[str, Any],
    api_key: Optional[str] = None,
    uipath_url: Optional[str] = None,
    uipath_access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a built-in tool by dynamically importing and calling the function.
    
    Args:
        python_function: Function path in one of these formats:
            - "google_search.google_search" (auto-prefixed with src.builtin)
            - "src.builtin.google_search.google_search" (full internal path)
            - "mcp_builtin_mycompany.my_tool" (external package, used as-is)
        arguments: Function arguments
        api_key: Optional API key for external services
        uipath_url: Optional UiPath Orchestrator URL (for UiPath tools)
        uipath_access_token: Optional UiPath access token (for UiPath tools)
        
    Returns:
        Dictionary containing execution results
        
    Example:
        # Internal tool
        result = await execute_builtin_tool(
            "google_search.google_search",
            {"q": "Python programming"},
            api_key="YOUR_API_KEY"
        )
        
        # External package tool
        result = await execute_builtin_tool(
            "mcp_builtin_mycompany.tools.my_tool",
            {"param1": "value"}
        )
    """
    try:
        logger.info(f"Executing built-in tool: {python_function}")
        logger.debug(f"Arguments: {arguments}")
        
        # Parse function path
        parts = python_function.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid function path: {python_function}")
        
        module_path, function_name = parts
        
        # Determine module path based on prefix
        if module_path.startswith(EXTERNAL_PACKAGE_PREFIX):
            # External package: use as-is
            logger.debug(f"External package detected: {module_path}")
        elif module_path.startswith("src.builtin"):
            # Already has full internal path
            logger.debug(f"Full internal path: {module_path}")
        elif module_path.startswith("builtin."):
            # Short form: builtin.xxx -> src.builtin.xxx
            module_path = f"src.{module_path}"
            logger.debug(f"Converted builtin path to: {module_path}")
        else:
            # Default: assume internal builtin
            module_path = f"src.builtin.{module_path}"
            logger.debug(f"Auto-prefixed module path: {module_path}")
        
        # Import module
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {e}")
            return {
                "success": False,
                "error": "Module not found",
                "message": f"Could not import module: {module_path}",
                "details": str(e)
            }
        
        # Get function
        if not hasattr(module, function_name):
            logger.error(f"Function {function_name} not found in module {module_path}")
            return {
                "success": False,
                "error": "Function not found",
                "message": f"Function '{function_name}' not found in module '{module_path}'"
            }
        
        func = getattr(module, function_name)
        
        # Check if function is callable
        if not callable(func):
            logger.error(f"{function_name} is not callable")
            return {
                "success": False,
                "error": "Not callable",
                "message": f"'{function_name}' is not a callable function"
            }
        
        # Add api_key to arguments if provided
        if api_key:
            arguments["api_key"] = api_key
        
        # Add UiPath credentials to arguments if this is a UiPath tool
        if "uipath_" in module_path:
            if uipath_url:
                arguments["uipath_url"] = uipath_url
                logger.debug(f"Added uipath_url to arguments")
            if uipath_access_token:
                arguments["access_token"] = uipath_access_token
                logger.debug(f"Added access_token to arguments")
        
        # Execute function
        logger.info(f"Calling {function_name} with arguments: {list(arguments.keys())}")
        
        # Check if function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            result = await func(**arguments)
        else:
            result = func(**arguments)
        
        logger.info(f"Built-in tool execution completed: {python_function}")
        
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            result = {"result": result}
        
        # Add success flag if not present
        if "success" not in result:
            result["success"] = True
        
        return result
        
    except TypeError as e:
        logger.error(f"Invalid arguments for {python_function}: {e}")
        return {
            "success": False,
            "error": "Invalid arguments",
            "message": f"Function call failed: {str(e)}",
            "function": python_function,
            "arguments": list(arguments.keys())
        }
    except Exception as e:
        logger.error(f"Error executing built-in tool {python_function}: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Execution failed",
            "message": str(e),
            "function": python_function
        }


def list_available_tools() -> Dict[str, Any]:
    """
    List all available built-in tools.
    
    Returns:
        Dictionary containing available tools information
    """
    try:
        from . import __all__ as available_tools
        
        return {
            "success": True,
            "tools": available_tools,
            "count": len(available_tools)
        }
    except Exception as e:
        logger.error(f"Error listing available tools: {e}")
        return {
            "success": False,
            "error": str(e),
            "tools": [],
            "count": 0
        }
