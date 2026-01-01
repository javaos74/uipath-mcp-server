# UiPath Queue Monitoring Tools

Built-in tools for monitoring UiPath Orchestrator queues.

## Overview

This module provides tools to monitor and analyze queue status in UiPath Orchestrator:
- Get queue health states
- Analyze queue statistics and SLA compliance

## Tools

### 1. uipath_get_queues_health_state

Get the health state of all queues from UiPath Orchestrator.

**Parameters:**
- `uipath_url` (string, required): UiPath Orchestrator URL (e.g., https://orchestrator.local)
- `access_token` (string, required): UiPath access token for authentication
- `time_frame_minutes` (integer, optional): Time frame in minutes (default: 1440 = 24 hours)
- `organization_unit_id` (integer, optional): Organization unit ID

**Returns:**
```json
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
```

**Health State Values:**
- `1`: Critical
- `2`: Warning
- `3`: Healthy

**Example Usage:**
```python
result = await get_queues_health_state(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token"
)

for item in result['data']:
    queue = item['data']
    print(f"{queue['queueName']}: Health State {queue['healthState']}")
```

### 2. uipath_get_queues_table

Get a paginated table of queues with statistics.

**Parameters:**
- `uipath_url` (string, required): UiPath Orchestrator URL (e.g., https://orchestrator.local)
- `access_token` (string, required): UiPath access token for authentication
- `time_frame_minutes` (integer, optional): Time frame in minutes (default: 1440 = 24 hours)
- `page_no` (integer, optional): Page number (default: 1)
- `page_size` (integer, optional): Number of items per page (default: 100)
- `organization_unit_id` (integer, optional): Organization unit ID

**Note:** Results are sorted by queue name in ascending order (fixed).

**Returns:**
```json
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
```

**Queue Statistics:**
- `countTotal`: Total number of queue items
- `countDeferred`: Number of deferred items
- `countOverdue`: Number of overdue items
- `countInSLA`: Number of items within SLA
- `ahtSeconds`: Average Handling Time in seconds
- `estimatedCompletionTime`: Estimated time to complete all items

**Example Usage:**
```python
# Get first page with default settings
result = await get_queues_table(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token"
)

# Get more queues per page
result = await get_queues_table(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token",
    page_size=200
)

# Get second page
result = await get_queues_table(
    uipath_url="https://orchestrator.local",
    access_token="your-access-token",
    page_no=2,
    page_size=100
)

print(f"Total queues: {result['total']}")
for queue in result['data']:
    print(f"{queue['queueName']}: {queue['countTotal']} items, {queue['countOverdue']} overdue")
```

## Installation

### 1. Add tools to database

```bash
cd backend
python scripts/add_uipath_queue_tools.py
```

### 2. Test the tools

```bash
cd backend
python scripts/test_uipath_queue_tools.py
```

## API Endpoints Used

### GetQueuesHealthState
- **Endpoint**: `/monitoring/QueuesMonitoring/GetQueuesHealthState`
- **Method**: POST
- **Body**: `{"timeFrameMinutes": "1440"}`
- **Authentication**: Bearer token
- **Description**: Returns health state of all queues

### GetQueuesTable
- **Endpoint**: `/monitoring/QueuesMonitoring/GetQueuesTable`
- **Method**: GET
- **Parameters**: `timeFrameMinutes`, `pageNo`, `pageSize`, `orderBy`, `direction` (query parameters)
- **Authentication**: Bearer token
- **Description**: Returns paginated table of queues with statistics

## Authentication

Both tools require a valid UiPath access token. The token can be obtained through:
1. Personal Access Token (PAT) from UiPath Cloud
2. OAuth 2.0 client credentials flow for on-premise installations

## SSL Certificate Handling

The tools automatically handle SSL certificates:
- **UiPath Cloud** (uipath.com): SSL verification enabled
- **On-Premise**: SSL verification disabled (supports self-signed certificates)

## Organization Unit Support

Both tools support multi-tenancy through the `organization_unit_id` parameter:
- If provided, filters queues for specific organization unit
- If omitted, returns queues from current context

## Sorting

The `get_queues_table` function returns results sorted by queue name in ascending order (fixed sorting).

## Pagination

The `get_queues_table` function supports pagination:
- Use `page_no` to navigate between pages
- Use `page_size` to control items per page
- Check `total` in response to know total number of queues

## Use Cases

### 1. Queue Health Monitoring
Monitor the overall health of queues to identify issues before they impact operations.

### 2. SLA Compliance
Track SLA compliance by monitoring overdue items and items within SLA.

### 3. Capacity Planning
Use average handling time and item counts to plan robot capacity.

### 4. Performance Analysis
Analyze queue processing performance over time to identify bottlenecks.

### 5. Alerting
Integrate with alerting systems to notify when queues have overdue items or health issues.

## Error Handling

The tools handle various error scenarios:
- HTTP errors (401, 403, 404, 500, etc.)
- Network errors (timeout, connection refused)
- Invalid responses
- Authentication failures

All errors are logged and returned with descriptive messages.

## Integration with MCP

These tools can be used as built-in tools in MCP servers, allowing AI assistants to:
- Query queue health status on demand
- Analyze queue statistics
- Provide insights on queue processing
- Answer questions about queue items and SLA compliance

## Limitations

- Requires valid UiPath Orchestrator access
- API endpoints may vary between UiPath versions
- Rate limiting may apply depending on Orchestrator configuration
- Health state values may vary between Orchestrator versions

## Future Enhancements

Potential additions:
- Get detailed queue item information
- Filter queues by folder or name
- Get queue item history
- Add/update queue items
- Retry failed queue items
- Get queue SLA configuration
