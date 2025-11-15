# UiPath Storage Bucket Tools

Built-in tools for managing UiPath Orchestrator storage buckets.

## Overview

Storage buckets in UiPath Orchestrator are used to store files and documents that can be accessed by automation processes. These tools allow you to:
- List and search storage buckets
- Get bucket details
- Generate upload URLs for file uploads (upload functionality to be added)

## Prerequisites

- **Organization Unit ID**: Required for all operations. Use `uipath_get_folder_id_by_name` to get the folder ID.
- **UiPath Access Token**: Valid authentication token
- **UiPath Orchestrator URL**: Base URL of your Orchestrator instance

## Tools

### 1. uipath_upload_file_to_storage_bucket

Upload a local file to a storage bucket using a pre-signed URL.

**Parameters:**
- `upload_url` (string, required): Pre-signed upload URL from `uipath_get_storage_bucket_upload_url`
- `local_file_path` (string, required): Full path to the local file to upload
- `content_type` (string, optional): MIME type (should match the one used to get upload URL)

**Example Request:**
```json
{
  "upload_url": "https://orchestrator.local/api/BlobFileAccess/Put?t=...",
  "local_file_path": "/home/user/documents/report.pdf",
  "content_type": "application/pdf"
}
```

**Example Request (Windows):**
```json
{
  "upload_url": "https://orchestrator.local/api/BlobFileAccess/Put?t=...",
  "local_file_path": "C:\\Users\\user\\Documents\\report.pdf",
  "content_type": "application/pdf"
}
```

**Example Response:**
```json
{
  "success": true,
  "message": "File uploaded successfully",
  "status_code": 200,
  "size_bytes": 12345,
  "local_file_path": "/home/user/documents/report.pdf",
  "file_deleted": true
}
```

**Use Cases:**
- Upload local files to storage bucket
- Complete the file upload workflow
- Store documents, reports, or data files in UiPath
- Automate file uploads from local file system
- Clean up local files after successful upload

**Important:**
- The file must exist on the local file system
- Provide the full absolute path to the file
- The function will read the file and upload it automatically
- **After successful upload, the local file will be automatically deleted**
- If file deletion fails, `file_deleted` will be `false` but upload is still successful

---

### 2. uipath_get_storage_buckets

Get a list of storage buckets, optionally filtered by name.

**Parameters:**
- `organization_unit_id` (integer, required): Organization unit ID (folder ID)
- `bucket_name` (string, optional): Bucket name to search for (partial match)
- `top` (integer, optional): Maximum number of results (default: 100)
- `skip` (integer, optional): Number of results to skip for pagination (default: 0)

**Example Request:**
```json
{
  "organization_unit_id": 1,
  "bucket_name": "demo",
  "top": 10
}
```

**Example Response:**
```json
{
  "count": 2,
  "buckets": [
    {
      "id": 2,
      "name": "demo",
      "description": "Demo bucket",
      "identifier": "99af4145-e4e4-4d8d-83a3-872b69a7f57f",
      "folders_count": 1,
      "storage_provider": null,
      "storage_container": null,
      "options": "None"
    },
    {
      "id": 1,
      "name": "poc",
      "description": "POC bucket",
      "identifier": "10cb35c5-6935-4adc-bfdf-081d9e1d883c",
      "folders_count": 1,
      "storage_provider": null,
      "storage_container": null,
      "options": "None"
    }
  ]
}
```

**Use Cases:**
- List all available storage buckets
- Search for specific buckets by name
- Get bucket IDs for file operations
- Check bucket configuration and folder associations

---

### 3. uipath_get_storage_bucket_by_name

Get storage bucket details by exact bucket name.

**Parameters:**
- `organization_unit_id` (integer, required): Organization unit ID (folder ID)
- `bucket_name` (string, required): Exact bucket name (case-sensitive)

**Example Request:**
```json
{
  "organization_unit_id": 1,
  "bucket_name": "poc"
}
```

**Example Response:**
```json
{
  "id": 1,
  "name": "poc",
  "description": "POC bucket",
  "identifier": "10cb35c5-6935-4adc-bfdf-081d9e1d883c",
  "folders_count": 1,
  "storage_provider": null,
  "storage_container": null,
  "options": "None"
}
```

**Use Cases:**
- Get bucket ID by name for file operations
- Verify bucket existence
- Get bucket configuration details
- Check bucket identifier (GUID)

---

### 4. uipath_get_storage_bucket_upload_url

Generate a pre-signed URL for uploading a file to a storage bucket.

**Parameters:**
- `organization_unit_id` (integer, required): Organization unit ID (folder ID)
- `bucket_id` (integer, required): Storage bucket ID
- `file_name` (string, required): File name with extension (e.g., "report.pdf", "data.xlsx", "image.png"). **This should be just the filename, not a full path.**
- `content_type` (string, optional): MIME type (default: "application/octet-stream")
- `directory` (string, optional): Directory name for organizing files. If not provided, a UUID will be auto-generated.

**Important:** 
- `file_name` should be **only the filename with extension**, not a full path (e.g., "report.pdf" not "/path/to/report.pdf")
- When uploading multiple files in the same session:
  - **Option 1**: Generate a UUID once and use it for all files
  - **Option 2**: Use the `directory` value from the first call's response for subsequent uploads

**Example Request (Single File):**
```json
{
  "organization_unit_id": 1,
  "bucket_id": 1,
  "file_name": "report.pdf",
  "content_type": "application/pdf"
}
```

**Example Request (Multiple Files - First File):**
```json
{
  "organization_unit_id": 1,
  "bucket_id": 1,
  "file_name": "report1.pdf",
  "content_type": "application/pdf",
  "directory": "my-session-2024"
}
```

**Example Request (Multiple Files - Second File):**
```json
{
  "organization_unit_id": 1,
  "bucket_id": 1,
  "file_name": "report2.pdf",
  "content_type": "application/pdf",
  "directory": "my-session-2024"
}
```

**Example Response:**
```json
{
  "uri": "https://orchestrator.local/api/BlobFileAccess/Put?t=d5bd4618-34f9-4a7a-841f-998407b81e71&r=...",
  "verb": "PUT",
  "headers": {},
  "directory": "my-session-2024",
  "full_path": "my-session-2024/report.pdf"
}
```

**Use Cases:**
- Prepare for file upload to storage bucket
- Get temporary upload URL with authentication
- Organize multiple files in the same directory
- First step in file upload workflow

**Note:** The actual file upload functionality will be added in a future update. Currently, this tool only generates the upload URL.

---

## Common Workflows

### Workflow 1: List All Buckets

```
1. Get folder ID:
   uipath_get_folder_id_by_name(folder_name="Shared")
   → Returns: folder_id = 1

2. List buckets:
   uipath_get_storage_buckets(organization_unit_id=1)
   → Returns: List of all buckets
```

### Workflow 2: Find Bucket by Name

```
1. Get folder ID:
   uipath_get_folder_id_by_name(folder_name="Shared")
   → Returns: folder_id = 1

2. Get bucket details:
   uipath_get_storage_bucket_by_name(
     organization_unit_id=1,
     bucket_name="poc"
   )
   → Returns: Bucket details with ID
```

### Workflow 3: Complete Single File Upload

```
1. Get folder ID:
   uipath_get_folder_id_by_name(folder_name="Shared")
   → Returns: folder_id = 1

2. Get bucket by name:
   uipath_get_storage_bucket_by_name(
     organization_unit_id=1,
     bucket_name="poc"
   )
   → Returns: bucket_id = 1

3. Get upload URL:
   uipath_get_storage_bucket_upload_url(
     organization_unit_id=1,
     bucket_id=1,
     file_name="report.pdf",
     content_type="application/pdf"
   )
   → Returns: Upload URL with auto-generated directory

4. Upload file:
   uipath_upload_file_to_storage_bucket(
     upload_url=<url from step 3>,
     local_file_path="/home/user/documents/report.pdf",
     content_type="application/pdf"
   )
   → Returns: Upload success status
```

### Workflow 4: Prepare Multiple Files Upload (Same Session)

```
1. Get folder ID and bucket ID (same as Workflow 3)

2. Generate session directory (or use UUID):
   directory = "my-upload-session-2024"

3. Get upload URL for first file:
   uipath_get_storage_bucket_upload_url(
     organization_unit_id=1,
     bucket_id=1,
     file_name="report1.pdf",
     content_type="application/pdf",
     directory="my-upload-session-2024"
   )
   → Returns: Upload URL with directory

4. Get upload URL for second file (reuse directory):
   uipath_get_storage_bucket_upload_url(
     organization_unit_id=1,
     bucket_id=1,
     file_name="report2.pdf",
     content_type="application/pdf",
     directory="my-upload-session-2024"
   )
   → Returns: Upload URL with same directory

5. Upload first file:
   uipath_upload_file_to_storage_bucket(
     upload_url=<url from step 3>,
     local_file_path="/home/user/documents/report1.pdf",
     content_type="application/pdf"
   )

6. Upload second file:
   uipath_upload_file_to_storage_bucket(
     upload_url=<url from step 4>,
     local_file_path="/home/user/documents/report2.pdf",
     content_type="application/pdf"
   )
   
Result: Both files will be in "my-upload-session-2024" directory
```

---

## Common MIME Types

| File Type | MIME Type |
|-----------|-----------|
| PDF | `application/pdf` |
| Excel | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| Word | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| CSV | `text/csv` |
| JSON | `application/json` |
| XML | `application/xml` |
| Text | `text/plain` |
| PNG | `image/png` |
| JPEG | `image/jpeg` |
| ZIP | `application/zip` |

---

## Error Handling

### Common Errors

1. **Bucket Not Found**
   ```json
   {
     "error": "Bucket 'xyz' not found"
   }
   ```
   **Solution**: Verify bucket name and organization unit ID

2. **Invalid Organization Unit ID**
   ```json
   {
     "error": "HTTP error occurred: 403 - Forbidden"
   }
   ```
   **Solution**: Use correct folder ID from `uipath_get_folder_id_by_name`

3. **Invalid Bucket ID**
   ```json
   {
     "error": "HTTP error occurred: 404 - Not Found"
   }
   ```
   **Solution**: Verify bucket ID exists in the specified folder

4. **File Not Found**
   ```json
   {
     "success": false,
     "error": "File not found: /path/to/file.pdf"
   }
   ```
   **Solution**: Verify the file path is correct and the file exists

5. **File Deletion Failed (Upload Successful)**
   ```json
   {
     "success": true,
     "message": "File uploaded successfully",
     "file_deleted": false
   }
   ```
   **Note**: Upload was successful but local file could not be deleted (e.g., permission issue)

---

## API Reference

### OData Endpoint
```
GET /odata/Buckets
```

**Query Parameters:**
- `$top`: Limit number of results
- `$skip`: Skip number of results
- `$filter`: OData filter expression
- `$orderby`: Sort order
- `$count`: Include total count

**Headers:**
- `Authorization`: Bearer token
- `x-uipath-organizationunitid`: Folder ID

### Upload URL Endpoint
```
GET /odata/Buckets({id})/UiPath.Server.Configuration.OData.GetWriteUri
```

**Query Parameters:**
- `path`: File path (URL encoded, with backslash prefix)
- `contentType`: MIME type (URL encoded)

---

## Future Enhancements

The following features are planned for future releases:

1. ✅ **File Upload**: Direct file upload to storage buckets (COMPLETED)
2. **File Download**: Download files from storage buckets
3. **File List**: List files in a storage bucket
4. **File Delete**: Delete files from storage buckets
5. **File Metadata**: Get file metadata (size, modified date, etc.)

---

## Related Tools

- **uipath_get_folders**: Get folder information
- **uipath_get_folder_id_by_name**: Get folder ID by name (required for organization_unit_id)

---

## Notes

- Storage buckets are folder-scoped resources
- Bucket names are case-sensitive
- File paths use backslash (`\`) as separator in UiPath
- Upload URLs are temporary and expire after a short time
- The `identifier` field is a GUID that uniquely identifies the bucket
