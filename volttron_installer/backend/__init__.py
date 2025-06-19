import reflex as rx
from fastapi import FastAPI
from . import endpoints as api
from .tool_manager import ToolManager
from .tool_router import tool_router

def init(app: FastAPI | rx.App):
    # Start the BACnet scan tool service
    # The tool should already be installed via pip install -e/pip install requirements.txt
    ToolManager.start_tool_service(
        module_path="bacnet_scan_tool.main:app",
        port=8001,
        # use_poetry=True  # Avoid this because using poetry within the app with no poetry lock file messes things up
    )
    
    # Reflex wraps fast API
    if isinstance(app, rx.App):
        app = app.api
    
    app.include_router(api.ansible_router, prefix="/api")
    app.include_router(api.platform_router, prefix="/api")
    app.include_router(api.task_router, prefix="/api")
    app.include_router(api.catalog_router, prefix="/api")
    
    app.include_router(tool_router, prefix="/tool")