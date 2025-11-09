# Built-in Tools Auto-Registration System

This directory contains built-in tools that are automatically discovered and registered to the database during initialization.

## How It Works

### 1. Tool Definition

Each Python module in this directory can define a `TOOLS` list with tool definitions:

```python
# Example: uipath_folder.py

async def get_folders(uipath_url: str, access_token: str, folder_name: str = None):
    """Get UiPath folders."""
    # Implementation...
    pass

TOOLS = [
    {
        "name": "uipath_get_folders",
        "description": "Get UiPath folders, optionally filtered by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_name": {
                    "type": "string",
                    "description": "Optional folder name to search for"
                }
            },
            "required": []
        },
        "function": get_folders  # Reference to the actual function
    }
]
```

### 2. Auto-Discovery

The `builtin_registry.py` module automatically:
- Scans all Python files in the `builtin/` directory
- Imports modules and looks for `TOOLS` definitions
- Extracts function references and converts them to module paths

### 3. Version-Based Migration

The system uses a simple version-based migration to avoid duplicate registrations:

```python
# In builtin_registry.py
BUILTIN_TOOLS_VERSION = 1  # Increment when adding/modifying tools
```

- When the database is initialized, it checks the current version
- If the version is outdated, it registers/updates all tools
- Version is stored in the `system_metadata` table

### 4. Database Registration

During `Database.initialize()`:
1. Creates all necessary tables
2. Calls `_register_builtin_tools()`
3. Discovers and registers tools if version is newer
4. Updates existing tools or creates new ones

## Adding New Built-in Tools

### Step 1: Create a new module

Create a new Python file in `backend/src/builtin/`:

```python
# backend/src/builtin/my_new_tool.py

async def my_function(param1: str, param2: int = 10):
    """My new tool function."""
    # Implementation
    return {"result": "success"}

TOOLS = [
    {
        "name": "my_new_tool",
        "description": "Description of what this tool does",
        "input_schema": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "First parameter"
                },
                "param2": {
                    "type": "integer",
                    "description": "Second parameter (optional)",
                    "default": 10
                }
            },
            "required": ["param1"]
        },
        "function": my_function
    }
]
```

### Step 2: Increment version

Edit `backend/src/builtin_registry.py`:

```python
# Increment this when adding/modifying tools
BUILTIN_TOOLS_VERSION = 2  # Changed from 1 to 2
```

### Step 3: Restart the application

The tools will be automatically registered on next startup!

## Testing

Test the auto-registration system:

```bash
python backend/scripts/test_builtin_registry.py
```

This will:
1. Discover all tools from builtin modules
2. Register them to the database
3. Verify registration
4. Test idempotency (running twice should not duplicate)

## Current Built-in Tools

### UiPath Folder Tools (2 tools)
- `uipath_get_folders` - List all folders
- `uipath_get_folder_id_by_name` - Find folder ID by name

### UiPath Job Tools (3 tools)
- `uipath_get_jobs_stats` - Job statistics by status
- `uipath_get_finished_jobs_evolution` - Job completion trends
- `uipath_get_processes_table` - Process execution summary

### UiPath Queue Tools (2 tools)
- `uipath_get_queues_health_state` - Queue health status
- `uipath_get_queues_table` - Queue items summary

### UiPath Schedule Tools (1 tool)
- `uipath_get_process_schedules` - Process schedule information

## Architecture

```
builtin/
├── README.md                    # This file
├── executor.py                  # Tool execution engine
├── uipath_folder.py            # Folder management tools
├── uipath_job.py               # Job monitoring tools
├── uipath_queue.py             # Queue monitoring tools
├── uipath_schedule.py          # Schedule monitoring tools
└── sample_apis/                # Sample API responses

builtin_registry.py             # Auto-discovery and registration
database.py                     # Database with version management
```

## Benefits

1. **No Manual Registration**: Just add a Python file with `TOOLS` definition
2. **Version Control**: Automatic migration based on version number
3. **Idempotent**: Safe to run multiple times
4. **Type Safe**: Function references ensure tools exist
5. **Easy Maintenance**: Update tools by editing Python files and incrementing version

## Notes

- Files starting with `_` or named `__init__.py` or `executor.py` are ignored
- The `function` field should reference the actual Python function
- The system automatically converts function references to module paths (e.g., `uipath_folder.get_folders`)
- Existing tools are updated, not duplicated
