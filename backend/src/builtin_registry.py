"""Built-in tools registry and auto-registration system.

This module automatically discovers and registers built-in tools from:
1. Internal builtin/ directory (legacy, will be deprecated)
2. External packages with prefix 'mcp_builtin_*'

External packages are synced based on their pip version - when a package
is updated, its tools are re-registered. When a package is removed,
its tools are deleted from the database.
"""

import importlib
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# External package prefix
EXTERNAL_PACKAGE_PREFIX = "mcp_builtin_"

# Internal tools version - increment when modifying internal builtin/ tools
# This will be deprecated once all tools are moved to external packages
INTERNAL_TOOLS_VERSION = 7


def _process_module_tools(module, module_name: str, source: str, source_package: str = None) -> List[Dict[str, Any]]:
    """Process TOOLS from a module and set python_function path.
    
    Args:
        module: Imported module object
        module_name: Full module name for logging
        source: Source identifier (e.g., filename or package name)
        source_package: Source package name for external packages
        
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
        tool_copy = tool.copy()
        # Set python_function path
        if "function" in tool_copy and callable(tool_copy["function"]):
            func = tool_copy["function"]
            tool_copy["_python_function"] = f"{func.__module__}.{func.__name__}"
        # Set source package
        if source_package:
            tool_copy["_source_package"] = source_package
        tools.append(tool_copy)
    
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
            tools.extend(_process_module_tools(module, module_name, py_file.name, source_package="internal"))
        except Exception as e:
            logger.error(f"  ✗ {py_file.name}: Failed to import - {e}")
    
    return tools


def _get_installed_external_packages() -> Dict[str, str]:
    """Get all installed mcp_builtin_* packages with their versions.
    
    Returns:
        Dictionary of package_name -> version
    """
    packages = {}
    
    # Try importlib.metadata first (Python 3.8+)
    try:
        from importlib.metadata import distributions
        for dist in distributions():
            # Convert package name: mcp-builtin-xxx -> mcp_builtin_xxx
            pkg_name = dist.metadata["Name"].lower().replace("-", "_")
            if pkg_name.startswith(EXTERNAL_PACKAGE_PREFIX):
                packages[pkg_name] = dist.version
        return packages
    except ImportError:
        pass
    
    # Fallback to pkg_resources
    try:
        import pkg_resources
        for dist in pkg_resources.working_set:
            pkg_name = dist.project_name.lower().replace("-", "_")
            if pkg_name.startswith(EXTERNAL_PACKAGE_PREFIX):
                packages[pkg_name] = dist.version
        return packages
    except ImportError:
        logger.warning("Neither importlib.metadata nor pkg_resources available")
        return packages


async def _discover_external_package_tools(pkg_name: str) -> List[Dict[str, Any]]:
    """Discover tools from a specific external package.
    
    Args:
        pkg_name: Package name (e.g., mcp_builtin_xxx)
        
    Returns:
        List of tool definitions from the package
    """
    tools = []
    
    try:
        # 1. Import package root (__init__.py)
        module = importlib.import_module(pkg_name)
        tools.extend(_process_module_tools(module, pkg_name, f"{pkg_name}/__init__.py", source_package=pkg_name))
        
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
                        submodule, submodule_name, f"{pkg_name}/{py_file.name}", source_package=pkg_name
                    ))
                except Exception as e:
                    logger.error(f"  ✗ {pkg_name}/{py_file.name}: Failed to import - {e}")
                    
    except Exception as e:
        logger.error(f"  ✗ {pkg_name}: Failed to import - {e}")
    
    return tools


async def _discover_external_builtin_packages() -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Discover built-in tools from all external mcp_builtin_* packages.
    
    Returns:
        Tuple of (tools list, packages dict with versions)
    """
    tools = []
    packages = _get_installed_external_packages()
    
    logger.info(f"Scanning {len(packages)} external mcp_builtin_* packages")
    
    for pkg_name in packages:
        logger.info(f"  Found external package: {pkg_name} v{packages[pkg_name]}")
        pkg_tools = await _discover_external_package_tools(pkg_name)
        tools.extend(pkg_tools)
    
    return tools, packages


async def discover_builtin_tools() -> List[Dict[str, Any]]:
    """Discover all built-in tools from internal and external sources.
    
    Returns:
        List of tool definitions from all sources
    """
    tools = []
    
    # 1. Internal builtin tools
    internal_tools = await _discover_internal_builtin_tools()
    tools.extend(internal_tools)
    logger.info(f"Discovered {len(internal_tools)} internal built-in tools")
    
    # 2. External package tools
    external_tools, _ = await _discover_external_builtin_packages()
    tools.extend(external_tools)
    logger.info(f"Discovered {len(external_tools)} external built-in tools")
    
    logger.info(f"Total discovered: {len(tools)} built-in tools")
    return tools


async def _register_tool(db, tool: Dict[str, Any]) -> bool:
    """Register or update a single tool in the database.
    
    Args:
        db: Database instance
        tool: Tool definition
        
    Returns:
        True if registered/updated successfully
    """
    python_function = tool.get("_python_function") or tool.get("python_function")
    
    if not python_function and "function" in tool:
        func = tool["function"]
        if callable(func):
            module_name = func.__module__
            func_name = func.__name__
            if module_name.startswith("src.builtin."):
                module_name = module_name.replace("src.builtin.", "")
            python_function = f"{module_name}.{func_name}"
    
    if not python_function:
        logger.error(f"  ✗ Failed to register {tool['name']}: No python_function found")
        return False
    
    source_package = tool.get("_source_package")
    
    # Check if tool already exists
    existing = await db.get_builtin_tool_by_name(tool["name"])
    
    if existing:
        await db.update_builtin_tool(
            tool_id=existing["id"],
            description=tool["description"],
            input_schema=tool["input_schema"],
            python_function=python_function,
            source_package=source_package,
        )
        logger.info(f"  ↻ Updated: {tool['name']}")
    else:
        await db.create_builtin_tool(
            name=tool["name"],
            description=tool["description"],
            input_schema=tool["input_schema"],
            python_function=python_function,
            source_package=source_package,
        )
        logger.info(f"  ✓ Registered: {tool['name']}")
    
    return True


async def sync_external_builtin_tools(db) -> Dict[str, Any]:
    """Sync external packages with the database.
    
    Compares installed package versions with stored versions and:
    - Registers tools from new packages
    - Updates tools from packages with version changes
    - Deletes tools from removed packages
    
    Args:
        db: Database instance
        
    Returns:
        Dictionary with sync results
    """
    logger.info("=== Syncing External Built-in Tools ===")
    
    # Get installed packages and their versions
    installed_packages = _get_installed_external_packages()
    logger.info(f"Found {len(installed_packages)} installed external packages")
    
    # Get stored package versions from database
    stored_versions = await db.get_all_external_package_versions()
    logger.info(f"Found {len(stored_versions)} stored package versions")
    
    registered_count = 0
    updated_packages = []
    new_packages = []
    removed_packages = []
    
    # Process installed packages
    for pkg_name, version in installed_packages.items():
        stored_version = stored_versions.get(pkg_name)
        
        if stored_version is None:
            # New package
            logger.info(f"  New package: {pkg_name} v{version}")
            new_packages.append(pkg_name)
            tools = await _discover_external_package_tools(pkg_name)
            for tool in tools:
                if await _register_tool(db, tool):
                    registered_count += 1
            await db.set_external_package_version(pkg_name, version)
            
        elif stored_version != version:
            # Updated package
            logger.info(f"  Updated package: {pkg_name} v{stored_version} -> v{version}")
            updated_packages.append(pkg_name)
            # Delete old tools and re-register
            deleted = await db.delete_builtin_tools_by_source_package(pkg_name)
            logger.info(f"    Deleted {deleted} old tools")
            tools = await _discover_external_package_tools(pkg_name)
            for tool in tools:
                if await _register_tool(db, tool):
                    registered_count += 1
            await db.set_external_package_version(pkg_name, version)
        else:
            logger.debug(f"  Unchanged: {pkg_name} v{version}")
    
    # Handle removed packages
    for pkg_name in stored_versions:
        if pkg_name not in installed_packages:
            logger.info(f"  Removed package: {pkg_name}")
            removed_packages.append(pkg_name)
            deleted = await db.delete_builtin_tools_by_source_package(pkg_name)
            logger.info(f"    Deleted {deleted} tools")
            await db.delete_external_package_version(pkg_name)
    
    logger.info(f"=== Sync Complete ===")
    logger.info(f"New: {len(new_packages)}, Updated: {len(updated_packages)}, Removed: {len(removed_packages)}")
    
    return {
        "new_packages": new_packages,
        "updated_packages": updated_packages,
        "removed_packages": removed_packages,
        "registered_tools": registered_count,
    }


async def register_internal_builtin_tools(db) -> int:
    """Register internal builtin tools (legacy support).
    
    Uses version-based migration to avoid duplicate registrations.
    
    Args:
        db: Database instance
        
    Returns:
        Number of tools registered
    """
    logger.info("=== Registering Internal Built-in Tools ===")
    
    # Check current version
    current_version = await db.get_builtin_tools_version()
    logger.info(f"Current version: {current_version}, Target version: {INTERNAL_TOOLS_VERSION}")
    
    if current_version >= INTERNAL_TOOLS_VERSION:
        logger.info("Internal tools are up to date, skipping registration")
        return 0
    
    # Discover internal tools
    tools = await _discover_internal_builtin_tools()
    
    if not tools:
        logger.warning("No internal built-in tools found")
        return 0
    
    # Register tools
    registered_count = 0
    for tool in tools:
        if await _register_tool(db, tool):
            registered_count += 1
    
    # Update version
    await db.set_builtin_tools_version(INTERNAL_TOOLS_VERSION)
    
    logger.info(f"Registered {registered_count} internal tools")
    return registered_count


async def ensure_builtin_tools_registered(db) -> None:
    """Ensure built-in tools are registered (called during database initialization).
    
    This function:
    1. Registers/updates internal builtin tools (version-based)
    2. Syncs external packages (version-based per package)
    
    Args:
        db: Database instance
    """
    try:
        # 1. Internal tools (legacy)
        internal_count = await register_internal_builtin_tools(db)
        if internal_count > 0:
            logger.info(f"✅ Registered {internal_count} internal built-in tools")
        
        # 2. External packages
        sync_result = await sync_external_builtin_tools(db)
        if sync_result["registered_tools"] > 0:
            logger.info(f"✅ Synced {sync_result['registered_tools']} external built-in tools")
            
    except Exception as e:
        logger.error(f"❌ Failed to register built-in tools: {e}", exc_info=True)


async def force_rediscover_builtin_tools(db) -> Dict[str, Any]:
    """Force re-discovery and registration of all built-in tools.
    
    Bypasses version checks and re-scans all sources.
    
    Args:
        db: Database instance
        
    Returns:
        Dictionary with discovery results
    """
    logger.info("=== Force Re-discovery of Built-in Tools ===")
    
    # 1. Re-register internal tools
    tools = await _discover_internal_builtin_tools()
    internal_count = 0
    for tool in tools:
        if await _register_tool(db, tool):
            internal_count += 1
    await db.set_builtin_tools_version(INTERNAL_TOOLS_VERSION)
    
    # 2. Force sync external packages (delete stored versions first)
    stored_versions = await db.get_all_external_package_versions()
    for pkg_name in stored_versions:
        await db.delete_external_package_version(pkg_name)
    
    sync_result = await sync_external_builtin_tools(db)
    
    return {
        "internal_tools": internal_count,
        "external_tools": sync_result["registered_tools"],
        "new_packages": sync_result["new_packages"],
        "message": f"Registered {internal_count} internal + {sync_result['registered_tools']} external tools"
    }
