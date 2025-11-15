"""UiPath Queue monitoring built-in tool.

This module provides tools for monitoring UiPath Orchestrator queues.
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
import urllib3
from urllib.parse import urlparse
import json

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


async def get_queues_health_state(
    uipath_url: str,
    access_token: str,
    folder_id: int,
    time_frame_minutes: int = 1440,
) -> Dict[str, Any]:
    """Get queues health state from UiPath Orchestrator.
    
    Retrieves the health state of all queues in the specified time frame.
    Health states indicate the overall status of queue processing.
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        folder_id: Folder ID (organization unit ID)
        time_frame_minutes: Time frame in minutes (default: 1440 = 24 hours)
        
    Returns:
        Dictionary containing queues health state data
        
    Example response:
        {
            "data": [
                {
                    "entityId": 2,
                    "data": {
                        "entityId": 2,
                        "queueName": "BusinessQueue",
                        "fullyQualifiedName": "Shared",
                        "folderId": 1,
                        "healthState": 3
                    }
                }
            ],
            "timeStamp": "2025-11-09T02:19:49.6498028Z",
            "total": null
        }
    """
    # Normalize URL
    base_url = uipath_url.rstrip('/')
    # Construct API endpoint
    parsed = urlparse(base_url)
    if len(parsed.path) <= 1:
        # MSI or simple URL
        api_url = f"{base_url}/monitoring/QueuesMonitoring/GetQueuesHealthState"
    else:
        # Automation Suite or Cloud
        api_url = f"{base_url}/orchestrator_/monitoring/QueuesMonitoring/GetQueuesHealthState"        
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "x-uipath-orchestrator": "true",
        "x-uipath-organizationunitid": str(folder_id),
    }
    
    body = {
        "timeFrameMinutes": str(time_frame_minutes)
    }
    
    try:
        # Determine if SSL verification should be disabled
        verify_ssl = "uipath.com" in base_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            logger.info(f"Fetching queues health state from: {api_url}")
            response = await client.post(api_url, headers=headers, json=body)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"Successfully retrieved queues health state: {len(result.get('data', []))} queues")
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


async def get_queues_table(
    uipath_url: str,
    access_token: str,
    folder_id: int,
    time_frame_minutes: int = 1440,
    page_no: int = 1,
    page_size: int = 100,
) -> Dict[str, Any]:
    """Get queues table with statistics from UiPath Orchestrator.
    
    Retrieves a paginated table of queues with their statistics including
    item counts, SLA status, average handling time, and estimated completion time.
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        folder_id: Folder ID (organization unit ID)
        time_frame_minutes: Time frame in minutes (default: 1440 = 24 hours)
        page_no: Page number (default: 1)
        page_size: Number of items per page (default: 100)
        
    Returns:
        Dictionary containing queues data and total count
        
    Example response:
        {
            "data": [
                {
                    "queueId": 3,
                    "queueName": "BusinessQueue",
                    "fullyQualifiedName": "Shared",
                    "countTotal": 16,
                    "countDeferred": 0,
                    "countOverdue": 0,
                    "countInSLA": 16,
                    "ahtSeconds": 0.05,
                    "estimatedCompletionTime": "2025-11-09T02:19:49.637Z"
                }
            ],
            "total": 2
        }
    """
    # Normalize URL
    base_url = uipath_url.rstrip('/')
    # Construct API endpoint
    parsed = urlparse(base_url)
    if len(parsed.path) <= 1:
        # MSI or simple URL
        api_url = f"{base_url}/monitoring/QueuesMonitoring/GetQueuesTable"
    else:
        # Automation Suite or Cloud
        api_url = f"{base_url}/orchestrator_/monitoring/QueuesMonitoring/GetQueuesTable"   
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "x-uipath-orchestrator": "true",
        "x-uipath-organizationunitid": str(folder_id),   
    }
    
    params = {
        "timeFrameMinutes": time_frame_minutes,
        "pageNo": page_no,
        "pageSize": page_size,
        "orderBy": "queueName",
        "direction": "asc",
    }
    
    try:
        # Determine if SSL verification should be disabled
        verify_ssl = "uipath.com" in base_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            logger.info(f"Fetching queues table from: {api_url} (page: {page_no}, size: {page_size})")
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"Successfully retrieved queues table: {result.get('total', 0)} total queues, {len(result.get('data', []))} in current page")
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
        "name": "uipath_get_queues_health_state",
        "description": "Get the health state of all queues from UiPath Orchestrator, indicating the overall status of queue processing",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_frame_minutes": {
                    "type": "integer",
                    "description": "Time frame in minutes (default: 1440 = 24 hours)",
                    "default": 1440
                },
                "folder_id": {
                    "type": "integer",
                    "description": "Folder ID (organization unit ID) - required"
                }
            },
            "required": ["folder_id"]
        },
        "function": get_queues_health_state
    },
    {
        "name": "uipath_get_queues_table",
        "description": "Get a paginated table of queues with statistics including item counts, SLA status, average handling time, and estimated completion time",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_frame_minutes": {
                    "type": "integer",
                    "description": "Time frame in minutes (default: 1440 = 24 hours)",
                    "default": 1440
                },
                "page_no": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of items per page (default: 100)",
                    "default": 100
                },
                "folder_id": {
                    "type": "integer",
                    "description": "Folder ID (organization unit ID) - required"
                }
            },
            "required": ["folder_id"]
        },
        "function": get_queues_table
    }
]
