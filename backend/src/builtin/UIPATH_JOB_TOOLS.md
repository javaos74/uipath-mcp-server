# UiPath Job Monitoring Tools

Built-in tools for monitoring UiPath Orchestrator jobs.

## Overview

This module provides tools to monitor and analyze job execution in UiPath Orchestrator:
- Get current job statistics by status
- Analyze job evolution over time

## Tools

### 1. uipath_get_jobs_stats

Get job statistics from UiPath Orchestrator showing counts by status.

**Parameters:**
- `uipath_url` (string, required): UiPath Orchestrator URL (e.g., https://orchestrator.local)
- `access_token` (string, required): UiPath access token for authentication

**Returns:**
```json
{
  "stats": [
    {"title": "Successful", "count": 745, "hasPermissions": true},
    {"title": "Faulted", "count": 833, "hasPermissions": true},
    {"title": "Stopped", "count": 9, "hasPermissions": true},
    {"title": "Running", "count": 0, "hasPermissions": true},
    {"title": "Pending", "count": 0, "hasPermissions": true}
  ],
  "total": 1587,
  "url": "https://orchestrator.local"
}
```

**Example Usage:**
```python
result = await get_jobs_stats(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token"
)
print(f"Total jobs: {result['total']}")
for stat in result['stats']:
    print(f"{stat['title']}: {stat['count']}")
```

### 2. uipath_get_finished_jobs_evolution

Get time-series data showing the evolution of finished jobs over a specified time period.

**Parameters:**
- `uipath_url` (string, required): UiPath Orchestrator URL (e.g., https://orchestrator.local)
- `access_token` (string, required): UiPath access token for authentication
- `time_frame_minutes` (integer, optional): Time frame in minutes (default: 1440 = 24 hours)

**Returns:**
```json
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
```

**Example Usage:**
```python
# Get last 24 hours
result = await get_finished_jobs_evolution(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token",
    time_frame_minutes=1440
)

# Get last 7 days
result = await get_finished_jobs_evolution(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token",
    time_frame_minutes=10080
)

# Calculate summary
total_successful = sum(item['countSuccessful'] for item in result)
total_errors = sum(item['countErrors'] for item in result)
print(f"Total successful: {total_successful}")
print(f"Total errors: {total_errors}")
print(f"Data points: {len(result)}")
```

### 3. uipath_get_processes_table

Get a paginated table of processes with job execution statistics.

**Parameters:**
- `uipath_url` (string, required): UiPath Orchestrator URL (e.g., https://orchestrator.local)
- `access_token` (string, required): UiPath access token for authentication
- `time_frame_minutes` (integer, optional): Time frame in minutes (default: 1440 = 24 hours)
- `page_no` (integer, optional): Page number (default: 1)
- `page_size` (integer, optional): Number of items per page (default: 100)

**Note:** Results are sorted by process name in ascending order (fixed).

**Returns:**
```json
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
```

**Example Usage:**
```python
# Get first page with default settings
result = await get_processes_table(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token"
)

# Get specific page with custom page size
result = await get_processes_table(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token",
    page_no=2,
    page_size=100
)

# Get more processes per page
result = await get_processes_table(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token",
    page_size=200
)

print(f"Total processes: {result['total']}")
for process in result['data']:
    print(f"{process['processName']}: {process['countSuccessful']} successful, {process['countErrors']} errors")
```

## Installation

### 1. Add tools to database

```bash
cd backend
python scripts/add_uipath_job_tools.py
```

### 2. Test the tools

```bash
cd backend
python scripts/test_uipath_job_tools.py
```

## API Endpoints Used

### GetJobsStats
- **Endpoint**: `/api/Stats/GetJobsStats`
- **Method**: GET
- **Authentication**: Bearer token
- **Description**: Returns job counts grouped by status

### GetFinishedJobsEvolution
- **Endpoint**: `/monitoring/JobsMonitoring/GetFinishedJobsEvolution`
- **Method**: GET
- **Parameters**: `timeFrameMinutes` (query parameter)
- **Authentication**: Bearer token
- **Description**: Returns time-series data of finished jobs

### GetProcessesTable
- **Endpoint**: `/monitoring/JobsMonitoring/GetProcessesTable`
- **Method**: GET
- **Parameters**: `timeFrameMinutes`, `pageNo`, `pageSize`, `orderBy`, `direction` (query parameters)
- **Authentication**: Bearer token
- **Description**: Returns paginated table of processes with job statistics

## Authentication

Both tools require a valid UiPath access token. The token can be obtained through:
1. Personal Access Token (PAT) from UiPath Cloud
2. OAuth 2.0 client credentials flow for on-premise installations

## SSL Certificate Handling

The tools automatically handle SSL certificates:
- **UiPath Cloud** (uipath.com): SSL verification enabled
- **On-Premise**: SSL verification disabled (supports self-signed certificates)

## Error Handling

The tools handle various error scenarios:
- HTTP errors (401, 403, 404, 500, etc.)
- Network errors (timeout, connection refused)
- Invalid responses
- Authentication failures

All errors are logged and returned with descriptive messages.

## Use Cases

### 1. Job Health Monitoring
Monitor the overall health of your automation environment by tracking job success/failure rates.

### 2. Trend Analysis
Analyze job execution trends over time to identify patterns and potential issues.

### 3. Capacity Planning
Use historical data to plan robot capacity and optimize resource allocation.

### 4. Alerting
Integrate with alerting systems to notify when error rates exceed thresholds.

### 5. Reporting
Generate reports on automation performance and ROI.

## Integration with MCP

These tools can be used as built-in tools in MCP servers, allowing AI assistants to:
- Query job statistics on demand
- Analyze job trends
- Provide insights on automation health
- Answer questions about job execution

## Limitations

- Requires valid UiPath Orchestrator access
- API endpoints may vary between UiPath versions
- Rate limiting may apply depending on Orchestrator configuration
- Time-series data granularity depends on Orchestrator settings

## Sorting

The `get_processes_table` function returns results sorted by process name in ascending order (fixed sorting).

## Pagination

The `get_processes_table` function supports pagination:
- Use `page_no` to navigate between pages
- Use `page_size` to control items per page
- Check `total` in response to know total number of processes

## Future Enhancements

Potential additions:
- Get detailed job information by ID
- Filter jobs by process, robot, or folder
- Get job execution logs
- Start/stop jobs
- Retry failed jobs
- Get job queue items
- Filter processes by name or folder
