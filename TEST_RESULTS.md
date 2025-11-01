# UiPath Process Listing - Test Results

## ✅ Test Passed!

### Test Environment
- **User**: charles (hyungsoo.kim@uipath.com)
- **UiPath URL**: https://cloud.uipath.com/uipathkor/UiPath
- **Database**: backend/mcp_servers.db

### Test Results
```
✓ Successfully connected to UiPath Cloud
✓ Retrieved 100 processes
✓ Process information includes:
  - Name
  - Version
  - Description
  - Input Parameters (auto-detected)
```

### Sample Processes Retrieved
1. PIPDemo2 (v1.0.5) - 2 parameters
2. RPA Challenge Studio Web (v1.0.1) - 2 parameters
3. FinacialTesting (v1.0.163060844) - 2 parameters
4. XPlatformTest (v1.0.10) - 2 parameters
5. AppsRequestTrigger (v1.0.1) - 2 parameters

## Implementation Details

### Backend Changes
1. **UiPathClient.list_processes()** - Added method to list processes
   - Uses httpx to call UiPath Orchestrator API directly
   - Endpoint: `/orchestrator_/odata/Releases`
   - Auto-detects input parameters from process arguments

2. **HTTP Server** - Added endpoint
   - `GET /api/uipath/processes` - Returns list of processes for current user

### Frontend Changes
1. **ServerDetail Page** - Complete rewrite
   - Shows list of registered tools
   - "Add Tool from UiPath Process" button

2. **UiPathProcessPicker Component** - New modal
   - Lists all UiPath processes
   - Shows process details (name, version, description, parameters)
   - Auto-generates tool name from process name
   - Auto-maps input parameters to MCP Tool schema

## How to Test

### 1. Start Backend
```bash
cd backend
source ../.venv/bin/activate
python -m src.main
```

### 2. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Test Flow
1. Login as charles (password: password123)
2. Go to Dashboard
3. Create a new MCP server
4. Click "Manage Tools"
5. Click "Add Tool from UiPath Process"
6. Select a process from the list
7. Review auto-generated tool configuration
8. Click "Create Tool"

## API Response Example

```json
{
  "count": 100,
  "processes": [
    {
      "id": "12345",
      "name": "PIPDemo2",
      "description": "Demo process",
      "version": "1.0.5",
      "key": "PIPDemo2",
      "input_parameters": [
        {
          "name": "param1",
          "type": "string",
          "description": "Parameter param1",
          "required": false
        }
      ]
    }
  ]
}
```

## Notes

- Database location: `backend/mcp_servers.db` (when running from backend folder)
- UiPath API uses Bearer token authentication
- Process parameters are auto-detected from Release arguments
- Duplicate processes (same ProcessKey) are filtered out
