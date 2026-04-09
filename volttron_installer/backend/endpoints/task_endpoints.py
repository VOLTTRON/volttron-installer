"""Task router and tool management router endpoints."""

import asyncio
from fastapi import APIRouter, HTTPException

from volttron_installer.backend.tool_manager import ToolManager

from ..models import (
    ReachableResponse,
    ToolRequest,
    ToolStatusResponse,
)

task_router = APIRouter(prefix="/task", tags=["tasks"])
tool_management_router = APIRouter(prefix="/manage_tools", tags=["manage tools"])


@task_router.get("/ping/{host_id}", response_model=ReachableResponse)
async def ping_resolvable_host(host_id: str):
    """
    Pings a specific host and returns if it's reachable

    Returns:
        ReachableResponse: Object containing a boolean 'reachable' field
    """
    try:
        # Run ping with a short timeout for faster response
        process = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", "3", host_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await asyncio.wait_for(process.communicate(), timeout=5)

        # If returncode is 0, the host is reachable
        return {"reachable": process.returncode == 0}

    except (asyncio.TimeoutError, Exception):
        # Timeout or any error means the host is not reachable
        return {"reachable": False}

@task_router.get("/")
async def get_tasks():
    """Retrieves the list of tasks"""
    # Get the list of tasks
    return {"tasks": []}

@task_router.get("/{id}")
async def task_status(id: str):
    """Retrieves the status of a specific task"""
    # Get the status of the task
    return {"status": "ok"}


@tool_management_router.post("/start_tool")
async def start_tool(request: ToolRequest):
    """Start a specific tool service on demand."""
    result = ToolManager.start_tool_service(
        tool_name=request.tool_name,
        module_path=request.module_path,
        use_poetry=request.use_poetry
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])

    return result

@tool_management_router.post("/stop_tool/{tool_name}", response_model=dict[str, str | bool])
async def stop_tool(tool_name: str):
    from loguru import logger
    """Stop a specific tool service."""
    result = ToolManager.stop_tool_service(tool_name=tool_name)
    logger.debug(result)
    if not result["success"] and "not running" not in result["message"]:
        raise HTTPException(status_code=404, detail=result["message"])

    if "not running" in result["message"]:
        return {"success": True, "message": f"Tool '{tool_name}' is already stopped"}

    return result

@tool_management_router.get("/tool_status/{tool_name}", response_model=ToolStatusResponse)
async def tool_status(tool_name: str):
    """Check if a specific tool is running."""
    is_running = ToolManager.is_tool_running(tool_name)
    if is_running:
        port = ToolManager.get_tool_port(tool_name) if is_running else None
        return ToolStatusResponse(
            tool_name= tool_name,
            tool_running=is_running,
            port=port
        )
    return ToolStatusResponse(
        tool_name= tool_name,
        tool_running=is_running,
        port=None
    )