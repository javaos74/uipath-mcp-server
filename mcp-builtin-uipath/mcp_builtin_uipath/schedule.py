"""UiPath Schedule monitoring built-in tool.

This module provides tools for monitoring UiPath Orchestrator process schedules.
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


async def get_process_schedules(
    uipath_url: str,
    access_token: str,
    folder_id: int,
    top: int = 100,
) -> List[Dict[str, Any]]:
    """Get process schedules from UiPath Orchestrator.
    
    Retrieves scheduled processes with their configuration including
    enabled status, release name, cron schedule, and next occurrence.
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        folder_id: Folder ID (organization unit ID) - required
        top: Maximum number of schedules to return (default: 100)
        
    Returns:
        List of schedule dictionaries with selected fields
        
    Example response:
        [
            {
                "enabled": true,
                "name": "DispatcherTrigger",
                "release_name": "DispatcherRetryQueue",
                "cron_summary": "Every 5 minutes",
                "next_occurrence": "2025-11-09T07:30:00Z"
            }
        ]
    """
    # Normalize URL
    base_url = uipath_url.rstrip('/')
    
    # Determine API endpoint based on URL structure
    parsed = urlparse(base_url)
    if len(parsed.path) <= 1:
        # MSI or simple URL
        api_url = f"{base_url}/odata/ProcessSchedules"
    else:
        # Automation Suite or Cloud
        api_url = f"{base_url}/orchestrator_/odata/ProcessSchedules"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-uipath-orchestrator": "true",
        "x-uipath-organizationunitid": str(folder_id),
    }
    
    params = {
        "$top": top,
        "$orderby": "Name asc",
    }
    
    try:
        # Determine if SSL verification should be disabled
        verify_ssl = "uipath.com" in base_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            logger.info(f"Fetching process schedules from: {api_url} (folder: {folder_id})")
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            schedules = data.get("value", [])
            
            # Extract only the required fields
            result = []
            for schedule in schedules:
                result.append({
                    "enabled": schedule.get("Enabled", False),
                    "name": schedule.get("Name", ""),
                    "release_name": schedule.get("ReleaseName", ""),
                    "cron_summary": schedule.get("StartProcessCronSummary", ""),
                    "next_occurrence": schedule.get("StartProcessNextOccurrence", ""),
                    "time_zone": schedule.get("TimeZoneId", "UTC"),
                })
            
            logger.info(f"Successfully retrieved {len(result)} process schedules")
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


# Tool definitions for MCP
TOOLS = [
    {
        "name": "uipath_get_process_schedules",
        "description": "Get process schedules from UiPath Orchestrator showing enabled status, release name, cron schedule summary, and next occurrence time",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "integer",
                    "description": "Folder ID (organization unit ID) - required"
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of schedules to return (default: 100)",
                    "default": 100
                }
            },
            "required": ["folder_id"]
        },
        "function": get_process_schedules
    }
]
