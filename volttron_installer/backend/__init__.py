import reflex as rx
from fastapi import FastAPI
from . import endpoints as api
from .tool_manager import ToolManager
from .tool_router import tool_router

def init(app: FastAPI | rx.App):

    # Tool configuration--bacnet scan tool
    ToolManager.start_tool_service(
        tool_name="bacnet-scan-tool",
        module_path="bacnet_scan_tool.main:app",
        port=8001
    )
    
    # Reflex wraps around the fastapi endpoint, so we gotta do some of this to add routes.
    if isinstance(app, rx.App):
        app = app.api
        
    app.include_router(api.ansible_router, prefix="/api")
    app.include_router(api.platform_router, prefix="/api")
    app.include_router(api.task_router, prefix="/api")
    app.include_router(api.catalog_router, prefix="/api")
    
    app.include_router(tool_router, prefix="/tool")