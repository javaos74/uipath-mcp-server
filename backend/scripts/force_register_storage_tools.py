"""Force register storage bucket tools."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database
from src.builtin_registry import discover_builtin_tools


async def main():
    """Force register storage bucket tools."""
    db_path = Path(__file__).parent.parent / "database" / "mcp_servers.db"
    db = Database(str(db_path))
    
    # Discover all tools
    print("Discovering tools...")
    tools = await discover_builtin_tools()
    
    # Filter storage bucket tools
    storage_tools = [t for t in tools if "storage" in t["name"].lower()]
    print(f"Found {len(storage_tools)} storage bucket tools:")
    for tool in storage_tools:
        print(f"  - {tool['name']}")
    
    # Register each storage tool
    print("\nRegistering storage bucket tools...")
    for tool in storage_tools:
        # Extract python_function
        python_function = tool.get("python_function")
        if not python_function and "function" in tool:
            func = tool["function"]
            if callable(func):
                module_name = func.__module__
                func_name = func.__name__
                if module_name.startswith("src.builtin."):
                    module_name = module_name.replace("src.builtin.", "")
                python_function = f"{module_name}.{func_name}"
        
        # Check if exists
        existing = await db.get_builtin_tool_by_name(tool["name"])
        
        if existing:
            print(f"  ↻ Updating: {tool['name']}")
            await db.update_builtin_tool(
                tool_id=existing["id"],
                description=tool["description"],
                input_schema=tool["input_schema"],
                python_function=python_function,
            )
        else:
            print(f"  ✓ Creating: {tool['name']}")
            await db.create_builtin_tool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["input_schema"],
                python_function=python_function,
            )
    
    # Update version
    await db.set_builtin_tools_version(6)
    print(f"\n✅ Done! Version set to 6")


if __name__ == "__main__":
    asyncio.run(main())
