"""Built-in tools registry and auto-registration system.

This module automatically discovers and registers built-in tools from:
1. Internal builtin/ directory
2. External packages with prefix 'mcp_builtin_*'

It uses a simple version-based migration system to avoid duplicate registrations.
"""

import os
import importlib
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Built-in tools version - increment this when adding/modifying tools
BUILTIN_TOOLS_VERSION = 7

# External package prefix
EXTERNAL_PACKAGE_PREFIX = "mcp_builtin_"


def _process_module_tools(module, module_name: str, source: str) -> List[Dict[str, Any]]:
    """Process TOOLS from a module and set python_function path.
    
    Args:
        module: Imported module object
        module_name: Full module name for logging
        source: Source identifier (e.g., filename or package name)
        
    Returns:
        List of processed tool definitions
    """
    tools = []
    
    if not hasattr(module, "TOOLS"):
        return tools
    
    module_tools = getattr(module, "TOOLS")
    if not isinstance(module_tools, list):
        logger.warning(f"  ✗ {source}: TOOLS is not a list")
        return tools
    
    for tool in module_tools:
        # Ensure python_function is set
        if "function" in tool and callable(tool["function"]):
            func = tool["function"]
            tool["_python_function"] = f"{func.__module__}.{func.__name__}"
        tools.append(tool)
    
    logger.info(f"  ✓ {source}: Found {len(module_tools)} tools")
    return tools


async def _discover_internal_builtin_tools() -> List[Dict[str, Any]]:
    """Discover built-in tools from internal builtin/ directory.
    
    Returns:
        List of tool definitions from internal builtin modules
    """
    tools = []
    builtin_dir = Path(__file__).parent / "builtin"
    
    # Find all Python files in builtin directory (excluding __init__.py and executor.py)
    python_files = [
        f for f in builtin_dir.glob("*.py")
        if f.name not in ["__init__.py", "executor.py"]
        and not f.name.startswith("_")
    ]
    
    logger.info(f"Scanning {len(python_files)} internal builtin modules")
    
    for py_file in python_files:
        module_name = f"src.builtin.{py_file.stem}"
        try:
            module = importlib.import_module(module_name)
            tools.extend(_process_module_tools(module, module_name, py_file.name))
        except Exception as e:
            logger.error(f"  ✗ {py_file.name}: Failed to import - {e}")
    
    return tools


async def _discover_external_builtin_packages() -> List[Dict[str, Any]]:
    """Discover built-in tools from external mcp_builtin_* packages.
    
    Scans installed packages with prefix 'mcp_builtin_' and imports their TOOLS definitions.
    Supports both __init__.py and submodule definitions.
    
    Returns:
        List of tool definitions from external packages
    """
    tools = []
    
    try:
        import pkg_resources
    except ImportError:
        logger.warning("pkg_resources not available, skipping external package discovery")
        return tools
    
    logger.info("Scanning external mcp_builtin_* packages")
    
    for dist in pkg_resources.working_set:
        # Convert package name: mcp-builtin-xxx -> mcp_builtin_xxx
        pkg_name = dist.project_name.lower().replace("-", "_")
        
        if not pkg_name.startswith(EXTERNAL_PACKAGE_PREFIX):
            continue
        
        logger.info(f"  Found external package: {dist.project_name} -> {pkg_name}")
        
        try:
            # 1. Import package root (__init__.py)
            module = importlib.import_module(pkg_name)
            tools.extend(_process_module_tools(module, pkg_name, f"{pkg_name}/__init__.py"))
            
            # 2. Scan submodules if package has __path__
            if hasattr(module, "__path__"):
                pkg_path = Path(module.__path__[0])
                for py_file in pkg_path.glob("*.py"):
                    if py_file.name.startswith("_"):
                        continue
                    
                    submodule_name = f"{pkg_name}.{py_file.stem}"
                    try:
                        submodule = importlib.import_module(submodule_name)
                        tools.extend(_process_module_tools(
                            submodule, submodule_name, f"{pkg_name}/{py_file.name}"
                        ))
                    except Exception as e:
                        logger.error(f"  ✗ {pkg_name}/{py_file.name}: Failed to import - {e}")
                        
        except Exception as e:
            logger.error(f"  ✗ {pkg_name}: Failed to import - {e}")
    
    return tools


async def discover_builtin_tools() -> List[Dict[str, Any]]:
    """Discover all built-in tools from internal and external sources.
    
    Scans:
    1. Internal builtin/ directory
    2. External mcp_builtin_* packages
    
    Returns:
        List of tool definitions from all sources
    """
    tools = []
    
    # 1. Internal builtin tools
    internal_tools = await _discover_internal_builtin_tools()
    tools.extend(internal_tools)
    logger.info(f"Discovered {len(internal_tools)} internal built-in tools")
    
    # 2. External package tools
    external_tools = await _discover_external_builtin_packages()
    tools.extend(external_tools)
    logger.info(f"Discovered {len(external_tools)} external built-in tools")
    
    logger.info(f"Total discovered: {len(tools)} built-in tools")
    return tools


async def register_builtin_tools(db, force: bool = False) -> int:
    """Register all discovered built-in tools to the database.
    
    Uses a version-based migration system to avoid duplicate registrations.
    Only registers tools if the current version is newer than the stored version,
    unless force=True.
    
    Args:
        db: Database instance
        force: If True, skip version check and force re-registration
        
    Returns:
        Number of tools registered
    """
    from .database import Database
    
    logger.info("=== Built-in Tools Registration ===")
    
    # Check current version in database (unless force mode)
    if not force:
        current_version = await db.get_builtin_tools_version()
        logger.info(f"Current version: {current_version}, Target version: {BUILTIN_TOOLS_VERSION}")
        
        if current_version >= BUILTIN_TOOLS_VERSION:
            logger.info("Built-in tools are up to date, skipping registration")
            return 0
    else:
        logger.info("Force mode enabled, skipping version check")
    
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
            # Extract python_function from _python_function (set by _process_module_tools)
            # or from function object directly
            python_function = tool.get("_python_function") or tool.get("python_function")
            
            if not python_function and "function" in tool:
                # Get function name from function object
                func = tool["function"]
                if callable(func):
                    module_name = func.__module__
                    func_name = func.__name__
                    # Keep full module path for external packages
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


async def force_rediscover_builtin_tools(db) -> Dict[str, Any]:
    """Force re-discovery and registration of all built-in tools.
    
    Bypasses version check and re-scans all sources (internal + external packages).
    Useful when new external packages are installed.
    
    Args:
        db: Database instance
        
    Returns:
        Dictionary with discovery results
    """
    logger.info("=== Force Re-discovery of Built-in Tools ===")
    
    # Discover all tools
    tools = await discover_builtin_tools()
    
    # Register with force=True
    registered_count = await register_builtin_tools(db, force=True)
    
    return {
        "discovered": len(tools),
        "registered": registered_count,
        "message": f"Discovered {len(tools)} tools, registered/updated {registered_count}"
    }


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
