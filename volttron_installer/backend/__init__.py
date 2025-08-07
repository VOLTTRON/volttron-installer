import reflex as rx
from fastapi import FastAPI
from . import endpoints as api
from .tool_router import tool_router
from .tool_manager import ToolManager
from loguru import logger
import os

def init(app: FastAPI | rx.App):
    # We grab the environment variable "TOOL_INACTIVITY_TIMEOUT" from our dev.env file. If value not present, we default to 30 seconds.
    try:
        timeout_value = os.environ.get("TOOL_INACTIVITY_TIMEOUT", "30")
        # Convert to int, and handle potential ValueError if the string can't be converted
        timeout_seconds = int(timeout_value)
        if timeout_seconds <= 0:
            # Validate that the timeout is positive
            logger.warning(f"Invalid TOOL_INACTIVITY_TIMEOUT value: {timeout_value}. Using default of 30 seconds.")
            timeout_seconds = 30
    except ValueError:
        # Handle case where the environment variable contains a non-integer value
        logger.warning(f"Non-numeric TOOL_INACTIVITY_TIMEOUT value: {timeout_value}. Using default of 30 seconds.")
        timeout_seconds = 30
        
    ToolManager.set_inactivity_timeout(timeout_seconds)

    # Reflex wraps fast API, make sure to set app to FastAPI instance
    if isinstance(app, rx.App):
        app = app.api

    app.include_router(api.ansible_router, prefix="/api")
    app.include_router(api.platform_router, prefix="/api")
    app.include_router(api.task_router, prefix="/api")
    app.include_router(api.catalog_router, prefix="/api")
    
    app.include_router(api.tool_management_router, prefix="/api")
    app.include_router(tool_router, prefix="/api")
    app.include_router(api.bacnet_scan_tool_router, prefix="/api")