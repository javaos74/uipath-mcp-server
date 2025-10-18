"""FastAPI application for managing RPA processes."""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os

from .database import Database
from .models import (
    ProcessCreate,
    ProcessUpdate,
    ProcessResponse,
    ProcessExecute,
    ProcessExecuteResponse
)
from .uipath_client import UiPathClient


app = FastAPI(
    title="UiPath Dynamic MCP Server API",
    description="API for managing and executing UiPath RPA processes",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and UiPath client
db = Database()
uipath_client = UiPathClient()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await db.initialize()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "UiPath Dynamic MCP Server API",
        "version": "0.1.0"
    }


@app.post("/processes", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
async def create_process(process: ProcessCreate):
    """Register a new RPA process.
    
    Args:
        process: Process creation data
        
    Returns:
        Created process data
    """
    # Check if process already exists
    existing = await db.get_process(process.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Process '{process.name}' already exists"
        )
    
    # Add to database
    input_params = [param.model_dump() for param in process.input_parameters]
    process_id = await db.add_process(
        name=process.name,
        description=process.description,
        folder_path=process.folder_path,
        input_parameters=input_params
    )
    
    # Retrieve and return created process
    created = await db.get_process(process.name)
    return ProcessResponse(**created)


@app.get("/processes", response_model=List[ProcessResponse])
async def list_processes():
    """List all registered processes.
    
    Returns:
        List of processes
    """
    processes = await db.list_processes()
    return [ProcessResponse(**p) for p in processes]


@app.get("/processes/{name}", response_model=ProcessResponse)
async def get_process(name: str):
    """Get a specific process by name.
    
    Args:
        name: Process name
        
    Returns:
        Process data
    """
    process = await db.get_process(name)
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process '{name}' not found"
        )
    return ProcessResponse(**process)


@app.put("/processes/{name}", response_model=ProcessResponse)
async def update_process(name: str, process_update: ProcessUpdate):
    """Update an existing process.
    
    Args:
        name: Process name
        process_update: Update data
        
    Returns:
        Updated process data
    """
    # Check if process exists
    existing = await db.get_process(name)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process '{name}' not found"
        )
    
    # Prepare update data
    input_params = None
    if process_update.input_parameters is not None:
        input_params = [param.model_dump() for param in process_update.input_parameters]
    
    # Update database
    await db.update_process(
        name=name,
        description=process_update.description,
        folder_path=process_update.folder_path,
        input_parameters=input_params
    )
    
    # Retrieve and return updated process
    updated = await db.get_process(name)
    return ProcessResponse(**updated)


@app.delete("/processes/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_process(name: str):
    """Delete a process.
    
    Args:
        name: Process name
    """
    deleted = await db.delete_process(name)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process '{name}' not found"
        )


@app.post("/processes/{name}/execute", response_model=ProcessExecuteResponse)
async def execute_process(name: str, execute_data: ProcessExecute):
    """Execute a registered RPA process.
    
    Args:
        name: Process name
        execute_data: Execution parameters
        
    Returns:
        Execution result
    """
    # Get process from database
    process = await db.get_process(name)
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process '{name}' not found"
        )
    
    try:
        # Execute process using UiPath client
        job = await uipath_client.execute_process(
            process_name=name,
            folder_path=process["folder_path"],
            input_arguments=execute_data.input_arguments
        )
        
        return ProcessExecuteResponse(
            job_id=job.get("id", ""),
            status=job.get("state", "Unknown"),
            message=f"Process '{name}' started successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute process: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
