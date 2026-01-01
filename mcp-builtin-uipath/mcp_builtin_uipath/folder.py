"""UiPath Folder management built-in tool.

This module provides tools for managing and querying UiPath Orchestrator folders.
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


async def get_folders(
    uipath_url: str,
    access_token: str,
    folder_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get UiPath folders, optionally filtered by name.
    
    Retrieves folders from UiPath Orchestrator. If folder_name is provided,
    filters results to folders matching the name (case-insensitive contains).
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        folder_name: Optional folder name to search for (partial match)
        
    Returns:
        List of folder dictionaries with id, name, full_name, description, type
    """
    # Normalize URL
    base_url = uipath_url.rstrip('/')
    
    # Determine API endpoint based on URL structure
    parsed = urlparse(base_url)
    if len(parsed.path) <= 1:
        api_url = f"{base_url}/odata/Folders"
    else:
        api_url = f"{base_url}/orchestrator_/odata/Folders"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    params = None
    if folder_name:
        escaped = folder_name.replace("'", "''")
        filter_expr = (
            f"contains(DisplayName,'{escaped}') or "
            f"contains(FullyQualifiedName,'{escaped}')"
        )
        params = {"$filter": filter_expr}
        logger.info(f"Searching folders with filter: {filter_expr}")
    
    try:
        verify_ssl = "uipath.com" in base_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            logger.info(f"Fetching folders from: {api_url}")
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            folders = data.get("value", [])
            
            result = []
            for folder in folders:
                result.append({
                    "id": str(folder.get("Id", "")),
                    "name": str(folder.get("DisplayName", folder.get("Name", ""))),
                    "full_name": str(folder.get("FullyQualifiedName", "")),
                    "description": str(folder.get("Description", "")),
                    "type": str(folder.get("Type", "")),
                })
            
            logger.info(f"Successfully retrieved {len(result)} folders")
            return result
            
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    except httpx.RequestError as e:
        error_msg = f"Request error occurred: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


async def get_folder_id_by_name(
    uipath_url: str,
    access_token: str,
    folder_name: str,
) -> Optional[str]:
    """Get folder ID by folder name (exact match, case-insensitive)."""
    try:
        folders = await get_folders(
            uipath_url=uipath_url,
            access_token=access_token,
            folder_name=folder_name,
        )
        
        folder_name_lower = folder_name.lower()
        for folder in folders:
            if folder["name"].lower() == folder_name_lower:
                logger.info(f"Found folder '{folder_name}' with ID: {folder['id']}")
                return folder["id"]
        
        for folder in folders:
            if folder["full_name"].lower() == folder_name_lower:
                logger.info(f"Found folder by full name '{folder_name}' with ID: {folder['id']}")
                return folder["id"]
        
        logger.warning(f"Folder '{folder_name}' not found")
        return None
        
    except Exception as e:
        logger.error(f"Error getting folder ID: {e}")
        raise


TOOLS = [
    {
        "name": "uipath_get_folders",
        "description": "Get UiPath folders, optionally filtered by name. Returns folder information including ID, name, and description.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_name": {
                    "type": "string",
                    "description": "Optional folder name to search for (partial match, case-insensitive)"
                }
            },
            "required": []
        },
        "function": get_folders
    },
    {
        "name": "uipath_get_folder_id_by_name",
        "description": "Get folder ID by exact folder name. Useful for finding the organization_unit_id needed for other UiPath tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_name": {
                    "type": "string",
                    "description": "Folder name to search for (exact match, case-insensitive)"
                }
            },
            "required": ["folder_name"]
        },
        "function": get_folder_id_by_name
    }
]
