"""Built-in tools registry and auto-registration system.

This module automatically discovers and registers built-in tools from the builtin/ directory.
It uses a simple version-based migration system to avoid duplicate registrations.
"""

import os
import importlib
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Built-in tools version - increment this when adding/modifying tools
BUILTIN_TOOLS_VERSION = 3


async def discover_builtin_tools() -> List[Dict[str, Any]]:
    """Discover all built-in tools from builtin/ directory.
    
    Scans all Python files in the builtin/ directory and imports their TOOLS definitions.
    
    Returns:
        List of tool definitions from all builtin modules
    """
    tools = []
    builtin_dir = Path(__file__).parent / "builtin"
    
    # Find all Python files in builtin directory (excluding __init__.py and executor.py)
    python_files = [
        f for f in builtin_dir.glob("*.py")
        if f.name not in ["__init__.py", "executor.py"]
        and not f.name.startswith("_")
    ]
    
    logger.info(f"Scanning {len(python_files)} builtin modules for TOOLS definitions")
    
    for py_file in python_files:
        module_name = f"src.builtin.{py_file.stem}"
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Check if module has TOOLS definition
            if hasattr(module, "TOOLS"):
                module_tools = getattr(module, "TOOLS")
                if isinstance(module_tools, list):
                    tools.extend(module_tools)
                    logger.info(f"  ✓ {py_file.name}: Found {len(module_tools)} tools")
                else:
                    logger.warning(f"  ✗ {py_file.name}: TOOLS is not a list")
            else:
                logger.debug(f"  - {py_file.name}: No TOOLS definition")
                
        except Exception as e:
            logger.error(f"  ✗ {py_file.name}: Failed to import - {e}")
    
    logger.info(f"Discovered {len(tools)} total built-in tools")
    return tools


async def register_builtin_tools(db) -> int:
    """Register all discovered built-in tools to the database.
    
    Uses a version-based migration system to avoid duplicate registrations.
    Only registers tools if the current version is newer than the stored version.
    
    Args:
        db: Database instance
        
    Returns:
        Number of tools registered
    """
    from .database import Database
    
    logger.info("=== Built-in Tools Registration ===")
    
    # Check current version in database
    current_version = await db.get_builtin_tools_version()
    logger.info(f"Current version: {current_version}, Target version: {BUILTIN_TOOLS_VERSION}")
    
    if current_version >= BUILTIN_TOOLS_VERSION:
        logger.info("Built-in tools are up to date, skipping registration")
        return 0
    
    # Discover all tools
    tools = await discover_builtin_tools()
    
    if not tools:
        logger.warning("No built-in tools found to register")
        return 0
    
    # Register each tool
    registered_count = 0
    skipped_count = 0
    
    for tool in tools:
        try:
            # Extract python_function from function object or string
            python_function = tool.get("python_function")
            if not python_function and "function" in tool:
                # Get function name from function object
                func = tool["function"]
                if callable(func):
                    # Get module and function name
                    module_name = func.__module__
                    func_name = func.__name__
                    # Convert to relative path format (e.g., "uipath_folder.get_folders")
                    if module_name.startswith("src.builtin."):
                        module_name = module_name.replace("src.builtin.", "")
                    python_function = f"{module_name}.{func_name}"
                else:
                    python_function = str(func)
            
            if not python_function:
                logger.error(f"  ✗ Failed to register {tool['name']}: No python_function found")
                skipped_count += 1
                continue
            
            # Check if tool already exists
            existing = await db.get_builtin_tool_by_name(tool["name"])
            
            if existing:
                # Update existing tool
                await db.update_builtin_tool(
                    tool_id=existing["id"],
                    description=tool["description"],
                    input_schema=tool["input_schema"],
                    python_function=python_function,
                )
                logger.info(f"  ↻ Updated: {tool['name']}")
                registered_count += 1
            else:
                # Create new tool
                await db.create_builtin_tool(
                    name=tool["name"],
                    description=tool["description"],
                    input_schema=tool["input_schema"],
                    python_function=python_function,
                )
                logger.info(f"  ✓ Registered: {tool['name']}")
                registered_count += 1
                
        except Exception as e:
            logger.error(f"  ✗ Failed to register {tool['name']}: {e}")
            skipped_count += 1
    
    # Update version in database
    await db.set_builtin_tools_version(BUILTIN_TOOLS_VERSION)
    
    logger.info(f"=== Registration Complete ===")
    logger.info(f"Registered/Updated: {registered_count}, Skipped: {skipped_count}")
    
    return registered_count


async def ensure_builtin_tools_registered(db) -> None:
    """Ensure built-in tools are registered (called during database initialization).
    
    This is a convenience wrapper around register_builtin_tools that can be called
    during database initialization without worrying about return values.
    
    Args:
        db: Database instance
    """
    try:
        count = await register_builtin_tools(db)
        if count > 0:
            logger.info(f"✅ Registered {count} built-in tools")
    except Exception as e:
        logger.error(f"❌ Failed to register built-in tools: {e}", exc_info=True)
