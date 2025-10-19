"""UiPath client wrapper for process execution."""

import os
import httpx
import logging
from typing import Dict, Any, Optional
from uipath import UiPath

logger = logging.getLogger(__name__)


class UiPathClient:
    """Wrapper for UiPath SDK client."""

    def __init__(self):
        """Initialize UiPath client."""
        self._sdk_cache: Dict[str, UiPath] = {}

    def _get_sdk(
        self,
        uipath_url: Optional[str] = None,
        uipath_access_token: Optional[str] = None,
    ) -> UiPath:
        """Get or create UiPath SDK instance.

        Args:
            uipath_url: UiPath Cloud URL (optional, uses env var if not provided)
            uipath_access_token: UiPath PAT (optional, uses env var if not provided)

        Returns:
            UiPath SDK instance
        """
        # Use provided credentials or fall back to environment variables
        url = uipath_url or os.getenv("UIPATH_URL")
        token = uipath_access_token or os.getenv("UIPATH_ACCESS_TOKEN")

        # Create cache key
        cache_key = f"{url}:{token[:10] if token else 'default'}"

        if cache_key not in self._sdk_cache:
            # Set environment variables for SDK
            if url:
                os.environ["UIPATH_URL"] = url
            if token:
                os.environ["UIPATH_ACCESS_TOKEN"] = token

            self._sdk_cache[cache_key] = UiPath()

        return self._sdk_cache[cache_key]

    async def execute_process(
        self,
        process_name: str,
        folder_path: str,
        input_arguments: Dict[str, Any],
        uipath_url: Optional[str] = None,
        uipath_access_token: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a UiPath process.

        Args:
            process_name: Name of the process to execute
            folder_path: UiPath folder path
            input_arguments: Input arguments for the process
            uipath_url: UiPath Cloud URL (optional)
            uipath_access_token: UiPath PAT (optional)
            folder_id: UiPath folder ID (optional)

        Returns:
            Job execution result with folder_id
        """
        logger.info(f"=== execute_process called ===")
        logger.info(f"Process: {process_name}")
        logger.info(f"Folder: {folder_path} (ID: {folder_id})")
        logger.info(f"Arguments: {input_arguments}")

        sdk = self._get_sdk(uipath_url, uipath_access_token)

        # Set folder path if provided
        if folder_path:
            os.environ["UIPATH_FOLDER_PATH"] = folder_path

        # Execute process
        logger.info(f"Invoking UiPath process...")
        job = sdk.processes.invoke(name=process_name, input_arguments=input_arguments)
        logger.info(
            f"Process invoked, job created: {job.id if hasattr(job, 'id') else 'N/A'}"
        )

        result = {
            "id": str(job.id) if hasattr(job, "id") else "",
            "state": str(job.state) if hasattr(job, "state") else "Unknown",
            "info": str(job.info) if hasattr(job, "info") else "",
            "folder_id": folder_id or "",
        }

        logger.info(f"Returning result: {result}")
        return result

    async def get_job_status(
        self,
        job_id: str,
        uipath_url: Optional[str] = None,
        uipath_access_token: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get job status using REST API.

        Args:
            job_id: Job ID
            uipath_url: UiPath Cloud URL (optional)
            uipath_access_token: UiPath PAT (optional)
            folder_id: UiPath folder ID (optional, for header)

        Returns:
            Job status information
        """
        logger.info(f"=== get_job_status called for job_id={job_id} ===")

        base_url = uipath_url or os.getenv("UIPATH_URL")
        token = uipath_access_token or os.getenv("UIPATH_ACCESS_TOKEN")

        if not base_url or not token:
            logger.error("UiPath URL and token are required but not provided")
            raise Exception("UiPath URL and token are required")

        # Construct API URL - using Jobs(id) endpoint
        api_url = f"{base_url}/orchestrator_/odata/Jobs({job_id})"
        logger.info(f"API URL: {api_url}")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Log headers (with partial token for security)
        log_headers = headers.copy()
        log_headers["Authorization"] = f"Bearer {token[:20] if token else 'None'}..."
        logger.info(f"Request headers: {log_headers}")

        # Add folder ID to header if provided
        if folder_id:
            headers["X-UIPATH-OrganizationUnitId"] = str(folder_id)
            logger.info(f"Using folder_id: {folder_id}")

        try:
            logger.info(f"Sending GET request to UiPath API...")
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, headers=headers, timeout=30.0)
                response.raise_for_status()
                job_data = response.json()

            logger.info(f"Received response: State={job_data.get('State', 'Unknown')}")

            # Parse output arguments if present
            output_args = None
            if "OutputArguments" in job_data and job_data["OutputArguments"]:
                try:
                    import json

                    output_args = (
                        json.loads(job_data["OutputArguments"])
                        if isinstance(job_data["OutputArguments"], str)
                        else job_data["OutputArguments"]
                    )
                except:
                    output_args = job_data["OutputArguments"]

            result = {
                "id": str(job_data.get("Id", job_id)),
                "state": str(job_data.get("State", "Unknown")),
                "info": str(job_data.get("Info", "")),
                "output_arguments": output_args,
            }

            logger.info(f"Returning job status: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}", exc_info=True)
            raise Exception(f"Failed to get job status: {str(e)}")

    async def list_folders(
        self,
        uipath_url: Optional[str] = None,
        uipath_access_token: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """List available UiPath folders.

        Args:
            uipath_url: UiPath Cloud URL (optional)
            uipath_access_token: UiPath PAT (optional)

        Returns:
            List of folder information
        """
        base_url = uipath_url or os.getenv("UIPATH_URL")
        token = uipath_access_token or os.getenv("UIPATH_ACCESS_TOKEN")

        if not base_url or not token:
            raise Exception("UiPath URL and token are required")

        # Construct API URL for folders
        api_url = f"{base_url}/orchestrator_/odata/Folders"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()

            folders = data.get("value", [])

            result = []
            for folder in folders:
                result.append(
                    {
                        "id": str(folder.get("Id", "")),
                        "name": str(folder.get("DisplayName", folder.get("Name", ""))),
                        "full_name": str(folder.get("FullyQualifiedName", "")),
                        "description": str(folder.get("Description", "")),
                        "type": str(folder.get("Type", "")),
                    }
                )

            return result
        except Exception as e:
            raise Exception(f"Failed to list folders: {str(e)}")

    async def list_processes(
        self,
        folder_id: str,
        uipath_url: Optional[str] = None,
        uipath_access_token: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """List available UiPath processes in a specific folder.

        Args:
            folder_id: UiPath folder ID (required)
            uipath_url: UiPath Cloud URL (optional)
            uipath_access_token: UiPath PAT (optional)

        Returns:
            List of process information
        """
        base_url = uipath_url or os.getenv("UIPATH_URL")
        token = uipath_access_token or os.getenv("UIPATH_ACCESS_TOKEN")

        if not base_url or not token:
            raise Exception("UiPath URL and token are required")

        if not folder_id:
            raise Exception("Folder ID is required")

        try:
            # First, get folder details to get the folder key
            folder_api_url = f"{base_url}/orchestrator_/odata/Folders({folder_id})"

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                # Get folder info
                folder_response = await client.get(
                    folder_api_url, headers=headers, timeout=30.0
                )
                folder_response.raise_for_status()
                folder_data = folder_response.json()

                # Now get releases with folder context
                # Use X-UIPATH-FolderPath header instead
                folder_path = folder_data.get("FullyQualifiedName", "")

                releases_headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-UIPATH-OrganizationUnitId": str(folder_id),
                }

                # Get releases for this folder
                releases_url = f"{base_url}/orchestrator_/odata/Releases"
                releases_response = await client.get(
                    releases_url, headers=releases_headers, timeout=30.0
                )
                releases_response.raise_for_status()
                data = releases_response.json()

            releases = data.get("value", [])

            result = []
            seen_keys = set()  # To avoid duplicates

            for release in releases:
                # Get unique process key
                process_key = release.get("ProcessKey")
                if not process_key or process_key in seen_keys:
                    continue

                seen_keys.add(process_key)

                # Extract input parameters from arguments
                input_params = []
                arguments = release.get("Arguments")
                if arguments:
                    try:
                        import json

                        args = (
                            json.loads(arguments)
                            if isinstance(arguments, str)
                            else arguments
                        )

                        if isinstance(args, dict):
                            # Check for Input (JSON string format) or InputArguments (dict format)
                            if "Input" in args:
                                # Input is a JSON string containing array of parameter definitions
                                input_str = args.get("Input")
                                if isinstance(input_str, str):
                                    input_array = json.loads(input_str)
                                    if isinstance(input_array, list):
                                        for param_def in input_array:
                                            if isinstance(param_def, dict):
                                                param_name = param_def.get("name", "")
                                                param_type_full = param_def.get(
                                                    "type", ""
                                                )
                                                param_required = param_def.get(
                                                    "required", False
                                                )
                                                param_has_default = param_def.get(
                                                    "hasDefault", False
                                                )

                                                # Parse .NET type to simple type
                                                param_type = "string"  # default
                                                if "System.String" in param_type_full:
                                                    param_type = "string"
                                                elif (
                                                    "System.Int" in param_type_full
                                                    or "System.Double"
                                                    in param_type_full
                                                    or "System.Decimal"
                                                    in param_type_full
                                                ):
                                                    param_type = "number"
                                                elif (
                                                    "System.Boolean" in param_type_full
                                                ):
                                                    param_type = "boolean"
                                                elif "[]" in param_type_full:
                                                    param_type = "array"
                                                elif (
                                                    "System.Object" in param_type_full
                                                    or "System.Collections"
                                                    in param_type_full
                                                ):
                                                    param_type = "object"

                                                input_params.append(
                                                    {
                                                        "name": param_name,
                                                        "type": param_type,
                                                        "description": f"Parameter {param_name}",
                                                        "required": param_required
                                                        and not param_has_default,
                                                    }
                                                )
                                elif isinstance(input_str, list):
                                    # Already parsed as list
                                    for param_def in input_str:
                                        if isinstance(param_def, dict):
                                            param_name = param_def.get("name", "")
                                            param_type_full = param_def.get("type", "")
                                            param_required = param_def.get(
                                                "required", False
                                            )
                                            param_has_default = param_def.get(
                                                "hasDefault", False
                                            )

                                            # Parse .NET type to simple type
                                            param_type = "string"
                                            if "System.String" in param_type_full:
                                                param_type = "string"
                                            elif (
                                                "System.Int" in param_type_full
                                                or "System.Double" in param_type_full
                                                or "System.Decimal" in param_type_full
                                            ):
                                                param_type = "number"
                                            elif "System.Boolean" in param_type_full:
                                                param_type = "boolean"
                                            elif "[]" in param_type_full:
                                                param_type = "array"
                                            elif (
                                                "System.Object" in param_type_full
                                                or "System.Collections"
                                                in param_type_full
                                            ):
                                                param_type = "object"

                                            input_params.append(
                                                {
                                                    "name": param_name,
                                                    "type": param_type,
                                                    "description": f"Parameter {param_name}",
                                                    "required": param_required
                                                    and not param_has_default,
                                                }
                                            )

                            elif "InputArguments" in args:
                                # InputArguments is a dict with key-value pairs
                                args_dict = args.get("InputArguments")
                                if isinstance(args_dict, dict):
                                    for key, value in args_dict.items():
                                        param_type = "string"
                                        if isinstance(value, bool):
                                            param_type = "boolean"
                                        elif isinstance(value, (int, float)):
                                            param_type = "number"
                                        elif isinstance(value, list):
                                            param_type = "array"
                                        elif isinstance(value, dict):
                                            param_type = "object"

                                        input_params.append(
                                            {
                                                "name": key,
                                                "type": param_type,
                                                "description": f"Parameter {key}",
                                                "required": False,
                                            }
                                        )
                    except Exception as e:
                        # Log error but continue processing
                        print(f"Error parsing arguments for {process_key}: {str(e)}")
                        pass

                result.append(
                    {
                        "id": str(release.get("Id", "")),
                        "name": str(release.get("Name", release.get("ProcessKey", ""))),
                        "description": str(release.get("Description", "")),
                        "version": str(
                            release.get("ProcessVersion", release.get("Version", ""))
                        ),
                        "key": str(process_key),
                        "input_parameters": input_params,
                    }
                )

            return result
        except Exception as e:
            raise Exception(f"Failed to list processes: {str(e)}")
