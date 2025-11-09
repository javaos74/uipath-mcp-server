"""UiPath Job monitoring built-in tool.

This module provides tools for monitoring UiPath Orchestrator jobs.
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


async def get_jobs_stats(
    uipath_url: str,
    access_token: str,
) -> Dict[str, Any]:
    """Get job statistics from UiPath Orchestrator.
    
    Retrieves the count of jobs by status (Successful, Faulted, Stopped, Running, etc.).
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        
    Returns:
        Dictionary containing job statistics by status
        
    Example response:
        {
            "stats": [
                {"title": "Successful", "count": 745, "hasPermissions": true},
                {"title": "Faulted", "count": 833, "hasPermissions": true},
                {"title": "Running", "count": 0, "hasPermissions": true}
            ],
            "total": 1587
        }
    """
    # Normalize URL
    base_url = uipath_url.rstrip('/')
    # Construct API endpoint
    parsed = urlparse(base_url)
    if len(parsed.path) <= 1:
        # MSI or simple URL
        api_url = f"{base_url}/api/Stats/GetJobsStats"
    else:
        # Automation Suite or Cloud
        api_url = f"{base_url}/orchestrator_/api/Stats/GetJobsStats"        
    #api_url = f"{base_url}/api/Stats/GetJobsStats"
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "x-uipath-orchestrator": "true",
    }
    
    try:
        # Determine if SSL verification should be disabled
        verify_ssl = "uipath.com" in base_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            logger.info(f"Fetching job stats from: {api_url}")
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            
            stats = response.json()
            
            # Calculate total
            total = sum(item.get("count", 0) for item in stats)
            
            result = {
                "stats": stats,
                "total": total,
                "url": base_url
            }
            
            logger.info(f"Successfully retrieved job stats: {total} total jobs")
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


async def get_finished_jobs_evolution(
    uipath_url: str,
    access_token: str,
    organization_unit_id: int,
    time_frame_minutes: int = 1440,
) -> List[Dict[str, Any]]:
    """Get finished jobs evolution over time from UiPath Orchestrator.
    
    Retrieves time-series data showing the evolution of finished jobs
    (successful, errors, stopped) over a specified time period.
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        time_frame_minutes: Time frame in minutes (default: 1440 = 24 hours)
        
    Returns:
        List of dictionaries containing time-series job evolution data
        
    Example response:
        [
            {
                "pointInTime": "2025-11-09T02:00:00Z",
                "countSuccessful": 6,
                "countErrors": 2,
                "countStopped": 0
            },
            {
                "pointInTime": "2025-11-09T03:19:39.04Z",
                "countSuccessful": 40,
                "countErrors": 24,
                "countStopped": 0
            }
        ]
    """
    # Normalize URL
    base_url = uipath_url.rstrip('/')
    # Construct API endpoint
    parsed = urlparse(base_url)
    if len(parsed.path) <= 1:
        # MSI or simple URL
        api_url = f"{base_url}/monitoring/JobsMonitoring/GetFinishedJobsEvolution"
    else:
        # Automation Suite or Cloud
        api_url = f"{base_url}/orchestrator_/monitoring/JobsMonitoring/GetFinishedJobsEvolution"
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "x-uipath-orchestrator": "true",
        "x-uipath-organizationunitid": str(organization_unit_id),
    }
    
    params = {
        "timeFrameMinutes": time_frame_minutes
    }
    
    try:
        # Determine if SSL verification should be disabled
        verify_ssl = "uipath.com" in base_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            logger.info(f"Fetching job evolution from: {api_url} (timeFrame: {time_frame_minutes} minutes)")
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            evolution = response.json()
            
            logger.info(f"Successfully retrieved job evolution: {len(evolution)} data points")
            return evolution
            
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


async def get_processes_table(
    uipath_url: str,
    access_token: str,
    organization_unit_id: int,
    time_frame_minutes: int = 1440,
    page_no: int = 1,
    page_size: int = 100,
) -> Dict[str, Any]:
    """Get processes table with job statistics from UiPath Orchestrator.
    
    Retrieves a paginated table of processes with their job execution statistics
    including counts by status, average duration, and average pending time.
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        time_frame_minutes: Time frame in minutes (default: 1440 = 24 hours)
        page_no: Page number (default: 1)
        page_size: Number of items per page (default: 100)
        
    Returns:
        Dictionary containing processes data and total count
        
    Example response:
        {
            "data": [
                {
                    "processId": 1,
                    "packageName": "MyProcess",
                    "processName": "MyProcess",
                    "fullyQualifiedName": "Shared",
                    "environmentName": null,
                    "countPending": 0,
                    "countSuspended": 0,
                    "countResumed": 0,
                    "countExecuting": 0,
                    "countSuccessful": 22,
                    "countStopped": 0,
                    "countErrors": 0,
                    "averageDurationInSeconds": 20,
                    "averagePendingTimeInSeconds": 11
                }
            ],
            "total": 5
        }
    """
    # Normalize URL
    base_url = uipath_url.rstrip('/')
    # Construct API endpoint
    parsed = urlparse(base_url)
    if len(parsed.path) <= 1:
        # MSI or simple URL
        api_url = f"{base_url}/monitoring/JobsMonitoring/GetProcessesTable"
    else:
        # Automation Suite or Cloud
        api_url = f"{base_url}/orchestrator_/monitoring/JobsMonitoring/GetProcessesTable"    
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "x-uipath-orchestrator": "true",
        "x-uipath-organizationunitid" : str(organization_unit_id),
    }

    params = {
        "timeFrameMinutes": time_frame_minutes,
        "pageNo": page_no,
        "pageSize": page_size,
        "orderBy": "processName",
        "direction": "asc",
    }
    
    try:
        # Determine if SSL verification should be disabled
        verify_ssl = "uipath.com" in base_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            logger.info(f"Fetching processes table from: {api_url} (page: {page_no}, size: {page_size})")
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"Successfully retrieved processes table: {result.get('total', 0)} total processes, {len(result.get('data', []))} in current page")
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
        "name": "uipath_get_jobs_stats",
        "description": "Get job statistics from UiPath Orchestrator showing counts by status (Successful, Faulted, Stopped, Running, Pending, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "function": get_jobs_stats
    },
    {
        "name": "uipath_get_finished_jobs_evolution",
        "description": "Get time-series data showing the evolution of finished jobs (successful, errors, stopped) over a specified time period",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_frame_minutes": {
                    "type": "integer",
                    "description": "Time frame in minutes (default: 1440 = 24 hours)",
                    "default": 1440
                },
                "organization_unit_id": {
                    "type": "integer",
                    "description": "Organization unit ID (required)"
                }
            },
            "required": [ "organization_unit_id"]
        },
        "function": get_finished_jobs_evolution
    },
    {
        "name": "uipath_get_processes_table",
        "description": "Get a paginated table of processes with job execution statistics including counts by status, average duration, and average pending time",
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
                "organization_unit_id": {
                    "type": "integer",
                    "description": "Organization unit ID (required)"
                }
            },
            "required": [ "organization_unit_id"]
        },
        "function": get_processes_table
    }
]
