"""UiPath Storage Bucket management built-in tool.

This module provides tools for managing and querying UiPath Orchestrator storage buckets.
Storage buckets are used to store files and documents in UiPath Orchestrator.
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, quote
import urllib3
import aiofiles

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


async def get_storage_buckets(
    uipath_url: str,
    access_token: str,
    folder_id: int,
    bucket_name: Optional[str] = None,
    top: int = 100,
    skip: int = 0,
    orderby: str = "Name asc",
) -> Dict[str, Any]:
    """Get UiPath storage buckets, optionally filtered by name.
    
    Retrieves storage buckets from UiPath Orchestrator. Storage buckets are used
    to store files and documents that can be accessed by automation processes.
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        folder_id: Folder ID (organization unit ID)
        bucket_name: Optional bucket name to search for (partial match)
        top: Maximum number of results to return (default: 100)
        skip: Number of results to skip for pagination (default: 0)
        orderby: OData orderby clause (default: "Name asc")
        
    Returns:
        Dictionary containing buckets list and total count
        
    Example response:
        {
            "count": 2,
            "buckets": [
                {
                    "id": 1,
                    "name": "poc",
                    "description": "POC bucket",
                    "identifier": "10cb35c5-6935-4adc-bfdf-081d9e1d883c",
                    "folders_count": 1,
                    "storage_provider": null,
                    "options": "None"
                },
                {
                    "id": 2,
                    "name": "demo",
                    "description": "Demo bucket",
                    "identifier": "99af4145-e4e4-4d8d-83a3-872b69a7f57f",
                    "folders_count": 1,
                    "storage_provider": null,
                    "options": "None"
                }
            ]
        }
    """
    # Normalize URL
    base_url = uipath_url.rstrip('/')
    
    # Determine API endpoint based on URL structure
    parsed = urlparse(base_url)
    if len(parsed.path) <= 1:
        # MSI or simple URL
        api_url = f"{base_url}/odata/Buckets"
    else:
        # Automation Suite or Cloud
        api_url = f"{base_url}/orchestrator_/odata/Buckets"
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "x-uipath-orchestrator": "true",
        "x-uipath-organizationunitid": str(organization_unit_id),
    }
    
    # Build OData query parameters
    params = {
        "$top": top,
        "$skip": skip,
        "$orderby": orderby,
        "$count": "true",
    }
    
    # Add filter if bucket_name is provided
    if bucket_name:
        # Escape single quotes per OData rules by doubling them
        escaped = bucket_name.replace("'", "''")
        params["$filter"] = f"contains(Name,'{escaped}')"
        logger.info(f"Searching buckets with filter: contains(Name,'{escaped}')")
    
    try:
        # Determine if SSL verification should be disabled
        verify_ssl = "uipath.com" in base_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            logger.info(f"Fetching storage buckets from: {api_url}")
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            buckets_raw = data.get("value", [])
            total_count = data.get("@odata.count", len(buckets_raw))
            
            # Transform to simplified format
            buckets = []
            for bucket in buckets_raw:
                buckets.append({
                    "id": bucket.get("Id"),
                    "name": bucket.get("Name", ""),
                    "description": bucket.get("Description", ""),
                    "identifier": bucket.get("Identifier", ""),
                    "folders_count": bucket.get("FoldersCount", 0),
                    "storage_provider": bucket.get("StorageProvider"),
                    "storage_container": bucket.get("StorageContainer"),
                    "options": bucket.get("Options", "None"),
                })
            
            result = {
                "count": total_count,
                "buckets": buckets,
            }
            
            logger.info(f"Successfully retrieved {len(buckets)} storage buckets (total: {total_count})")
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


async def get_storage_bucket_by_name(
    uipath_url: str,
    access_token: str,
    folder_id: int,
    bucket_name: str,
) -> Optional[Dict[str, Any]]:
    """Get storage bucket by exact name.
    
    Searches for a storage bucket by name and returns its details if found.
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        folder_id: Folder ID (organization unit ID)
        bucket_name: Bucket name to search for (exact match, case-sensitive)
        
    Returns:
        Bucket dictionary if found, None otherwise
        
    Example:
        bucket = await get_storage_bucket_by_name(
            uipath_url="https://orchestrator.local",
            access_token="token",
            folder_id=1,
            bucket_name="poc"
        )
        # Returns: {"id": 1, "name": "poc", ...}
    """
    try:
        # Get all buckets matching the name
        result = await get_storage_buckets(
            uipath_url=uipath_url,
            access_token=access_token,
            folder_id=folder_id,
            bucket_name=bucket_name,
        )
        
        # Find exact match (case-sensitive)
        for bucket in result["buckets"]:
            if bucket["name"] == bucket_name:
                logger.info(f"Found bucket '{bucket_name}' with ID: {bucket['id']}")
                return bucket
        
        logger.warning(f"Bucket '{bucket_name}' not found")
        return None
        
    except Exception as e:
        logger.error(f"Error getting bucket by name: {e}")
        raise


async def upload_file_to_storage_bucket(
    uipath_url: str,
    access_token: str, 
    upload_url: str,
    local_file_path: str,
    content_type: str = "application/octet-stream",
) -> Dict[str, Any]:
    """Upload file to storage bucket using pre-signed URL.
    
    This is the second step in the file upload process. Use the URL obtained from
    get_storage_bucket_upload_url() to upload the actual file.
    
    The function reads the file from the local file system, uploads it to the
    storage bucket, and then deletes the local file upon successful upload.
    
    Args:
        uipath_url, access_token : unused for this api but executor needs them 
        upload_url: Pre-signed upload URL from get_storage_bucket_upload_url()
        local_file_path: Full path to the local file to upload (e.g., "/home/user/documents/report.pdf")
        content_type: MIME type of the file (should match the one used to get upload URL)
        
    Returns:
        Dictionary containing upload status
        
    Example response:
        {
            "success": True,
            "message": "File uploaded successfully",
            "status_code": 200,
            "size_bytes": 12345,
            "local_file_path": "/home/user/documents/report.pdf",
            "file_deleted": True
        }
        
    Note:
        After successful upload, the local file will be automatically deleted.
        If file deletion fails, file_deleted will be False but the upload is still successful.
        
    Example usage:
        # Step 1: Get upload URL
        upload_info = await get_storage_bucket_upload_url(
            uipath_url="https://orchestrator.local",
            access_token="token",
            folder_id=1,
            bucket_id=1,
            file_name="report.pdf",
            content_type="application/pdf"
        )
        
        # Step 2: Upload file
        result = await upload_file_to_storage_bucket(
            upload_url=upload_info["uri"],
            local_file_path="/home/user/documents/report.pdf",
            content_type="application/pdf"
        )
    """
    import os
    import aiofiles
    
    headers = {
        "content-type": content_type,
    }
    
    try:
        # Check if file exists
        if not os.path.exists(local_file_path):
            error_msg = f"File not found: {local_file_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }
        
        # Check if it's a file (not a directory)
        if not os.path.isfile(local_file_path):
            error_msg = f"Path is not a file: {local_file_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }
        
        # Get file size
        file_size = os.path.getsize(local_file_path)
        
        # Read file content
        async with aiofiles.open(local_file_path, 'rb') as f:
            file_content = await f.read()
        
        # Determine if SSL verification should be disabled
        # Check if it's a local/self-signed certificate
        verify_ssl = "uipath.com" in upload_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=300.0) as client:
            logger.info(f"Uploading file '{local_file_path}' to storage bucket (size: {file_size} bytes)")
            response = await client.put(upload_url, headers=headers, content=file_content)
            response.raise_for_status()
            
            # Upload successful - delete local file
            try:
                os.remove(local_file_path)
                logger.info(f"Deleted local file after successful upload: {local_file_path}")
                file_deleted = True
            except Exception as delete_error:
                logger.warning(f"Failed to delete local file '{local_file_path}': {delete_error}")
                file_deleted = False
            
            result = {
                "success": True,
                "message": "File uploaded successfully",
                "status_code": response.status_code,
                "size_bytes": file_size,
                "local_file_path": local_file_path,
                "file_deleted": file_deleted,
            }
            
            logger.info(f"Successfully uploaded file '{local_file_path}' ({file_size} bytes)")
            return result
            
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "status_code": e.response.status_code,
            "local_file_path": local_file_path,
        }
    except httpx.RequestError as e:
        error_msg = f"Request error occurred: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "local_file_path": local_file_path,
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "local_file_path": local_file_path,
        }


async def get_storage_bucket_upload_url(
    uipath_url: str,
    access_token: str,
    folder_id: int,
    bucket_id: int,
    file_name: str,
    content_type: str = "application/octet-stream",
    directory: Optional[str] = None,
) -> Dict[str, Any]:
    """Get upload URL for a file in a storage bucket.
    
    Generates a pre-signed URL that can be used to upload a file to the storage bucket.
    This is the first step in the file upload process.
    
    The directory parameter is used to organize files in the bucket. If not provided,
    a UUID will be automatically generated. When uploading multiple files in the same
    session, use the same directory value to keep them organized together.
    
    Args:
        uipath_url: UiPath Orchestrator URL (e.g., https://orchestrator.local)
        access_token: UiPath access token for authentication
        folder_id: Folder ID (organization unit ID)
        bucket_id: Storage bucket ID
        file_name: File name with extension (e.g., "report.pdf", "data.xlsx", "image.png").
                   This should be just the filename, not a full path.
        content_type: MIME type of the file (default: "application/octet-stream")
        directory: Optional directory name for organizing files. If not provided, a UUID will be generated.
                   Use the same directory value for multiple files in the same session.
        
    Returns:
        Dictionary containing upload URL, HTTP verb, and directory used
        
    Example response:
        {
            "uri": "https://orchestrator.local/api/BlobFileAccess/Put?t=...",
            "verb": "PUT",
            "headers": {},
            "directory": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "full_path": "a1b2c3d4-e5f6-7890-abcd-ef1234567890/report.pdf"
        }
        
    Example usage:
        # Single file upload
        upload_info = await get_storage_bucket_upload_url(
            uipath_url="https://orchestrator.local",
            access_token="token",
            organization_unit_id=1,
            bucket_id=1,
            file_name="report.pdf",
            content_type="application/pdf"
        )
        # directory will be auto-generated
        
        # Multiple files in same session
        # First file
        upload_info1 = await get_storage_bucket_upload_url(
            uipath_url="https://orchestrator.local",
            access_token="token",
            folder_id=1,
            bucket_id=1,
            file_name="report1.pdf",
            content_type="application/pdf",
            directory="my-session-2024"  # or use UUID from first call
        )
        
        # Second file - use same directory
        upload_info2 = await get_storage_bucket_upload_url(
            uipath_url="https://orchestrator.local",
            access_token="token",
            folder_id=1,
            bucket_id=1,
            file_name="report2.pdf",
            content_type="application/pdf",
            directory=upload_info1["directory"]  # reuse directory
        )
    """
    import uuid
    
    # Generate directory if not provided
    if not directory:
        directory = str(uuid.uuid4())
        logger.info(f"Generated directory UUID: {directory}")
    
    # Normalize URL
    base_url = uipath_url.rstrip('/')
    
    # Construct full path: directory/file_name
    full_path = f"{directory}/{file_name}"
    
    # Encode file path for URL
    # Note: UiPath expects backslash as path separator
    encoded_path = quote(f"\\{full_path}")
    encoded_content_type = quote(content_type)
    
    # Determine API endpoint based on URL structure
    parsed = urlparse(base_url)
    if len(parsed.path) <= 1:
        # MSI or simple URL
        api_url = f"{base_url}/odata/Buckets({bucket_id})/UiPath.Server.Configuration.OData.GetWriteUri"
    else:
        # Automation Suite or Cloud
        api_url = f"{base_url}/orchestrator_/odata/Buckets({bucket_id})/UiPath.Server.Configuration.OData.GetWriteUri"
    
    # Add query parameters
    api_url = f"{api_url}?path={encoded_path}&contentType={encoded_content_type}"
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "x-uipath-orchestrator": "true",
        "x-uipath-organizationunitid": str(folder_id),
    }
    
    try:
        # Determine if SSL verification should be disabled
        verify_ssl = "uipath.com" in base_url.lower()
        
        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            logger.info(f"Getting upload URL for bucket {bucket_id}, path: {full_path}")
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            result = {
                "uri": data.get("Uri", ""),
                "verb": data.get("Verb", "PUT"),
                "headers": data.get("Headers", {}),
                "directory": directory,
                "full_path": full_path,
            }
            
            logger.info(f"Successfully generated upload URL for {full_path} (directory: {directory})")
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
        "name": "uipath_upload_file_to_storage_bucket",
        "description": "Upload a local file to a storage bucket using a pre-signed URL. This is the second step after getting the upload URL. The function reads the file from the local file system and uploads it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "upload_url": {
                    "type": "string",
                    "description": "Pre-signed upload URL from uipath_get_storage_bucket_upload_url"
                },
                "local_file_path": {
                    "type": "string",
                    "description": "Full path to the local file to upload (e.g., '/home/user/documents/report.pdf', 'C:\\Users\\user\\Documents\\report.pdf') - required"
                },
                "content_type": {
                    "type": "string",
                    "description": "MIME type of the file (should match the one used to get upload URL). Default: 'application/octet-stream'",
                    "default": "application/octet-stream"
                }
            },
            "required": ["upload_url", "local_file_path", "content_type"]
        },
        "function": upload_file_to_storage_bucket
    },
    {
        "name": "uipath_get_storage_buckets",
        "description": "Get UiPath storage buckets contain id, name and description, optionally filtered by name. ",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "integer",
                    "description": "Folder ID (organization unit ID)"
                },
                "bucket_name": {
                    "type": "string",
                    "description": "Optional bucket name to search for (partial match)"
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 100)",
                    "default": 100
                },
                "skip": {
                    "type": "integer",
                    "description": "Number of results to skip for pagination (default: 0)",
                    "default": 0
                }
            },
            "required": ["folder_id"]
        },
        "function": get_storage_buckets
    },
    {
        "name": "uipath_get_storage_bucket_by_name",
        "description": "Get storage bucket details  by exact bucket name. Returns bucket information including ID, identifier, and folder count.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "integer",
                    "description": "Folder ID (organization unit ID)"
                },
                "bucket_name": {
                    "type": "string",
                    "description": "Bucket name to search for (exact match, case-sensitive)"
                }
            },
            "required": ["folder_id", "bucket_name"]
        },
        "function": get_storage_bucket_by_name
    },
    {
        "name": "uipath_get_storage_bucket_upload_url",
        "description": "Get a pre-signed upload URL for uploading a file to a storage bucket. This is the first step in the file upload process. The returned URL can be used to upload file content via HTTP PUT request. IMPORTANT: When uploading multiple files in the same session, either generate a UUID once and reuse it for the 'directory' parameter, or use the 'directory' value returned from the first call for subsequent uploads to keep files organized together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "integer",
                    "description": "Folder ID (organization unit ID) - required"
                },
                "bucket_id": {
                    "type": "integer",
                    "description": "Storage bucket ID - required"
                },
                "file_name": {
                    "type": "string",
                    "description": "File name with extension (e.g., 'report.pdf', 'data.xlsx', 'image.png'). This should be just the filename, not a full path - required"
                },
                "content_type": {
                    "type": "string",
                    "description": "MIME type of the file (e.g., 'application/pdf', 'image/png'). Default: 'application/octet-stream'",
                    "default": "application/octet-stream"
                },
                "directory": {
                    "type": "string",
                    "description": "Optional directory name for organizing files. If not provided, a UUID will be auto-generated. For multiple files in the same session, use the same directory value (either generate a UUID once or reuse the 'directory' from the first call's response)."
                }
            },
            "required": ["folder_id", "bucket_id", "file_name", "content_type"]
        },
        "function": get_storage_bucket_upload_url
    }
]
