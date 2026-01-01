# UiPath Folder Management Tools

Built-in tools for managing and querying UiPath Orchestrator folders.

## Overview

This module provides tools to query folder information from UiPath Orchestrator:
- List all folders or search by name
- Get folder ID by exact name (useful for finding organization_unit_id)

## Tools

### 1. uipath_get_folders

Get UiPath folders, optionally filtered by name.

**Parameters:**
- `folder_name` (string, optional): Folder name to search for (partial match, case-insensitive)

**Returns:**
```json
[
  {
    "id": "1",
    "name": "Shared",
    "full_name": "Shared",
    "description": "Default shared folder",
    "type": "Personal"
  },
  {
    "id": "2",
    "name": "Production",
    "full_name": "Production",
    "description": "Production environment",
    "type": "Directory"
  }
]
```

**Example Usage:**
```python
# Get all folders
folders = await get_folders(
    uipath_url="https://orchestrator.local",
    access_token="your-token"
)

# Search for folders containing "Shared"
folders = await get_folders(
    uipath_url="https://orchestrator.local",
    access_token="your-token",
    folder_name="Shared"
)

for folder in folders:
    print(f"{folder['name']} (ID: {folder['id']})")
```

### 2. uipath_get_folder_id_by_name

Get folder ID by exact folder name. This is particularly useful for finding the `organization_unit_id` parameter needed for other UiPath tools like queue and job monitoring.

**Parameters:**
- `folder_name` (string, required): Folder name to search for (exact match, case-insensitive)

**Returns:**
- Folder ID as string, or `null` if not found

**Example Response:**
```json
"1"
```

**Example Usage:**
```python
# Get folder ID for "Shared" folder
folder_id = await get_folder_id_by_name(
    uipath_url="https://orchestrator.local",
    access_token="your-token",
    folder_name="Shared"
)

if folder_id:
    print(f"Folder ID: {folder_id}")
    # Use this ID as organization_unit_id in other tools
else:
    print("Folder not found")
```

## Use Cases

### 1. Finding Organization Unit ID

Many UiPath monitoring tools require an `organization_unit_id` parameter. Use `uipath_get_folder_id_by_name` to find the ID:

```python
# Step 1: Get folder ID
folder_id = await get_folder_id_by_name(
    uipath_url="https://orchestrator.local",
    access_token="your-token",
    folder_name="Production"
)

# Step 2: Use it in queue monitoring
queues = await get_queues_table(
    uipath_url="https://orchestrator.local",
    access_token="your-token",
    organization_unit_id=int(folder_id)
)
```

### 2. Listing Available Folders

Get an overview of all folders in the Orchestrator:

```python
folders = await get_folders(
    uipath_url="https://orchestrator.local",
    access_token="your-token"
)

print(f"Found {len(folders)} folders:")
for folder in folders:
    print(f"  - {folder['name']} ({folder['type']})")
```

### 3. Searching for Specific Folders

Find folders matching a search term:

```python
# Find all folders with "prod" in the name
prod_folders = await get_folders(
    uipath_url="https://orchestrator.local",
    access_token="your-token",
    folder_name="prod"
)
```

## Installation

### 1. Add tools to database

```bash
cd backend
python scripts/add_uipath_folder_tools.py
```

### 2. Test the tools

```bash
cd backend
python scripts/test_uipath_folder_tools.py
```

## API Endpoint Used

### Folders (OData)
- **Endpoint**: `/odata/Folders` (MSI) or `/orchestrator_/odata/Folders` (Cloud/Suite)
- **Method**: GET
- **Parameters**: `$filter` (OData query parameter for filtering)
- **Authentication**: Bearer token
- **Description**: Returns folder information from Orchestrator

## Authentication

Both tools require a valid UiPath access token. The token can be obtained through:
1. Personal Access Token (PAT) from UiPath Cloud
2. OAuth 2.0 client credentials flow for on-premise installations

## SSL Certificate Handling

The tools automatically handle SSL certificates:
- **UiPath Cloud** (uipath.com): SSL verification enabled
- **On-Premise**: SSL verification disabled (supports self-signed certificates)

## Folder Types

UiPath folders can have different types:
- **Personal**: User-specific folders
- **Directory**: Shared folders for teams
- **Modern**: Modern folder structure (UiPath 2021.10+)

## Search Behavior

The `folder_name` parameter in `uipath_get_folders`:
- Performs partial match (contains)
- Case-insensitive
- Searches both DisplayName and FullyQualifiedName fields

The `folder_name` parameter in `uipath_get_folder_id_by_name`:
- Performs exact match
- Case-insensitive
- Returns first match if multiple folders have the same name

## Error Handling

The tools handle various error scenarios:
- HTTP errors (401, 403, 404, 500, etc.)
- Network errors (timeout, connection refused)
- Invalid responses
- Authentication failures

All errors are logged and returned with descriptive messages.

## Integration with Other Tools

These folder tools are designed to work seamlessly with other UiPath monitoring tools:

```python
# Example: Get queues for a specific folder
folder_id = await get_folder_id_by_name(
    uipath_url="https://orchestrator.local",
    access_token="token",
    folder_name="Production"
)

if folder_id:
    queues = await get_queues_table(
        uipath_url="https://orchestrator.local",
        access_token="token",
        organization_unit_id=int(folder_id)
    )
```

## Limitations

- Requires valid UiPath Orchestrator access
- API endpoints may vary between UiPath versions
- Rate limiting may apply depending on Orchestrator configuration
- Folder structure depends on Orchestrator version (Classic vs Modern folders)

## Future Enhancements

Potential additions:
- Create new folders
- Update folder properties
- Delete folders
- Get folder permissions
- List users in folder
