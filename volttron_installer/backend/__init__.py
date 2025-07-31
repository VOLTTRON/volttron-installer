import reflex as rx
from fastapi import FastAPI
from . import endpoints as api
from .tool_router import tool_router
from .tool_manager import ToolManager
import os

def init(app: FastAPI | rx.App):
    ToolManager.set_inactivity_timeout(int(os.environ.get("TOOL_INACTIVITY_TIMEOUT", 30)))
    
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