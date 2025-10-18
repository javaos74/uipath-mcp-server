"""MCP Server that dynamically exposes registered UiPath processes as tools."""

from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import asyncio

from .database import Database
from .uipath_client import UiPathClient


# Initialize MCP server
mcp = FastMCP("UiPath Dynamic Process Server")

# Initialize database and UiPath client
db = Database()
uipath_client = UiPathClient()


async def init_db():
    """Initialize database."""
    await db.initialize()


# Initialize database on startup
asyncio.run(init_db())


@mcp.tool()
async def list_available_processes() -> Dict[str, Any]:
    """List all registered UiPath processes.
    
    Returns:
        Dictionary containing list of available processes
    """
    processes = await db.list_processes()
    return {
        "count": len(processes),
        "processes": [
            {
                "name": p["name"],
                "description": p["description"],
                "input_parameters": p["input_parameters"]
            }
            for p in processes
        ]
    }


@mcp.tool()
async def execute_uipath_process(
    process_name: str,
    input_arguments: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Execute a registered UiPath process.
    
    Args:
        process_name: Name of the process to execute
        input_arguments: Input arguments for the process (optional)
        
    Returns:
        Execution result with job information
    """
    if input_arguments is None:
        input_arguments = {}
    
    # Get process from database
    process = await db.get_process(process_name)
    if not process:
        return {
            "success": False,
            "error": f"Process '{process_name}' not found"
        }
    
    try:
        # Execute process
        job = await uipath_client.execute_process(
            process_name=process_name,
            folder_path=process["folder_path"],
            input_arguments=input_arguments
        )
        
        return {
            "success": True,
            "job_id": job.get("id", ""),
            "status": job.get("state", "Unknown"),
            "message": f"Process '{process_name}' started successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_process_info(process_name: str) -> Dict[str, Any]:
    """Get detailed information about a registered process.
    
    Args:
        process_name: Name of the process
        
    Returns:
        Process information including parameters
    """
    process = await db.get_process(process_name)
    if not process:
        return {
            "success": False,
            "error": f"Process '{process_name}' not found"
        }
    
    return {
        "success": True,
        "process": {
            "name": process["name"],
            "description": process["description"],
            "folder_path": process["folder_path"],
            "input_parameters": process["input_parameters"],
            "created_at": process["created_at"],
            "updated_at": process["updated_at"]
        }
    }


# Run the MCP server
if __name__ == "__main__":
    mcp.run()
