# UiPath Schedule Monitoring Tools

Built-in tools for monitoring UiPath Orchestrator process schedules.

## Overview

This module provides tools to monitor scheduled processes in UiPath Orchestrator, showing when processes are scheduled to run and their configuration.

## Tools

### uipath_get_process_schedules

Get process schedules from UiPath Orchestrator.

**Parameters:**
- `organization_unit_id` (integer, required): Organization unit ID (folder ID)
- `top` (integer, optional): Maximum number of schedules to return (default: 100)

**Returns:**
```json
[
  {
    "enabled": true,
    "name": "DispatcherTrigger",
    "release_name": "DispatcherRetryQueue",
    "cron_summary": "Every 5 minutes",
    "next_occurrence": "2025-11-09T07:30:00Z"
  },
  {
    "enabled": true,
    "name": "ProcessorRetryQueue",
    "release_name": "ProcessorRetryQueue",
    "cron_summary": "Every minute",
    "next_occurrence": "2025-11-09T07:30:00Z"
  }
]
```

**Fields:**
- `enabled`: Whether the schedule is active
- `name`: Schedule name
- `release_name`: Name of the process/release being scheduled
- `cron_summary`: Human-readable schedule description (e.g., "Every 5 minutes")
- `next_occurrence`: Next scheduled execution time (ISO 8601 format)

**Example Usage:**
```python
# Get schedules for folder ID 1
schedules = await get_process_schedules(
    uipath_url="https://orchestrator.local",
    access_token="your-token",
    organization_unit_id=1
)

for schedule in schedules:
    status = "Enabled" if schedule['enabled'] else "Disabled"
    print(f"{schedule['name']} ({status}): {schedule['cron_summary']}")
    print(f"  Next run: {schedule['next_occurrence']}")
```

## Finding Organization Unit ID

Use the `uipath_get_folder_id_by_name` tool to find the organization_unit_id:

```python
# Step 1: Get folder ID
folder_id = await get_folder_id_by_name(folder_name="Production")

# Step 2: Get schedules for that folder
schedules = await get_process_schedules(
    organization_unit_id=int(folder_id)
)
```

## Installation

### 1. Add tools to database

```bash
cd backend
python scripts/add_uipath_schedule_tools.py
```

### 2. Test the tools

```bash
cd backend
python scripts/test_uipath_schedule_tools.py
```

## API Endpoint Used

### ProcessSchedules (OData)
- **Endpoint**: `/odata/ProcessSchedules` (MSI) or `/orchestrator_/odata/ProcessSchedules` (Cloud/Suite)
- **Method**: GET
- **Parameters**: `$top`, `$orderby` (OData query parameters)
- **Headers**: `x-uipath-organizationunitid` (required)
- **Authentication**: Bearer token
- **Description**: Returns scheduled process information

## Authentication

The tool requires a valid UiPath access token. The token can be obtained through:
1. Personal Access Token (PAT) from UiPath Cloud
2. OAuth 2.0 client credentials flow for on-premise installations

## SSL Certificate Handling

The tool automatically handles SSL certificates:
- **UiPath Cloud** (uipath.com): SSL verification enabled
- **On-Premise**: SSL verification disabled (supports self-signed certificates)

## Use Cases

### 1. Schedule Monitoring
Monitor which processes are scheduled to run and when.

### 2. Schedule Validation
Verify that critical processes have active schedules.

### 3. Next Occurrence Tracking
Check when processes are scheduled to run next.

### 4. Schedule Auditing
Review all scheduled processes in a folder for compliance.

### 5. Capacity Planning
Understand process execution patterns for resource planning.

## Error Handling

The tool handles various error scenarios:
- HTTP errors (401, 403, 404, 500, etc.)
- Network errors (timeout, connection refused)
- Invalid responses
- Authentication failures
- Missing organization_unit_id

All errors are logged and returned with descriptive messages.

## Integration with MCP

This tool can be used as a built-in tool in MCP servers, allowing AI assistants to:
- Query scheduled processes on demand
- Check when processes will run next
- Verify schedule configurations
- Answer questions about process automation schedules

## Limitations

- Requires valid UiPath Orchestrator access
- Requires organization_unit_id (folder ID)
- API endpoints may vary between UiPath versions
- Rate limiting may apply depending on Orchestrator configuration
- Results are sorted by name in ascending order (fixed)

## Future Enhancements

Potential additions:
- Enable/disable schedules
- Update schedule configuration
- Create new schedules
- Delete schedules
- Get schedule execution history
- Filter schedules by enabled status or release name
