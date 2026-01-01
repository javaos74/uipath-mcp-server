# MCP Built-in UiPath Tools

UiPath Orchestrator built-in tools for MCP server.

## Installation

```bash
pip install mcp-builtin-uipath
# or for development
pip install -e ./mcp-builtin-uipath
```

## Available Tools

### Folder Tools
- `uipath_get_folders` - List all folders
- `uipath_get_folder_id_by_name` - Find folder ID by name

### Job Tools
- `uipath_get_jobs_stats` - Job statistics by status
- `uipath_get_finished_jobs_evolution` - Job completion trends
- `uipath_get_processes_table` - Process execution summary

### Queue Tools
- `uipath_get_queues_health_state` - Queue health status
- `uipath_get_queues_table` - Queue items summary

### Schedule Tools
- `uipath_get_process_schedules` - Process schedule information

### Storage Bucket Tools
- `uipath_upload_file_to_storage_bucket` - Upload file to storage bucket
- `uipath_download_file_from_storage_bucket` - Download file from storage bucket
- `uipath_list_storage_bucket_files` - List files in storage bucket
- `uipath_delete_storage_bucket_file` - Delete file from storage bucket

## Usage

Once installed, the MCP server will automatically discover and register these tools on startup.

To manually trigger re-discovery:
```bash
curl -X POST http://localhost:8000/api/builtin-tools/rediscover \
  -H "Authorization: Bearer <admin_token>"
```
