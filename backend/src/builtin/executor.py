"""Built-in tool executor."""

import logging
import importlib
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def execute_builtin_tool(
    python_function: str,
    arguments: Dict[str, Any],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a built-in tool by dynamically importing and calling the function.
    
    Args:
        python_function: Function path in one of these formats:
            - "google_search.google_search" (recommended, auto-prefixed with src.builtin)
            - "src.builtin.google_search.google_search" (full path, also supported)
        arguments: Function arguments
        api_key: Optional API key for external services
        
    Returns:
        Dictionary containing execution results
        
    Example:
        result = await execute_builtin_tool(
            "google_search.google_search",
            {"q": "Python programming"},
            api_key="YOUR_API_KEY"
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
        
        # Auto-prefix with src.builtin if not already prefixed
        if not module_path.startswith("src.builtin."):
            # Check if it's already a full path starting with src.builtin
            if module_path.startswith("src.builtin"):
                # Already has prefix, use as-is
                pass
            else:
                # Add src.builtin prefix
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
