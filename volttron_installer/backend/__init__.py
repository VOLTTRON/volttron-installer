import reflex as rx
from fastapi import FastAPI
from contextlib import asynccontextmanager
from . import endpoints as api
from .tool_router import tool_router
from .tool_manager import ToolManager

# Cleanup after shutdown
@asynccontextmanager
async def tools_lifespan(app):
    # Startup
    yield
    # Shutdown of the tools
    ToolManager.stop_all_tools()

def init(app: FastAPI | rx.App, inactivity_timeout_minutes: int = 30):
    ToolManager.set_inactivity_timeout(inactivity_timeout_minutes)
    
    # Reflex wraps fast API, make sure to set app to FastAPI instance
    if isinstance(app, rx.App):
        app = app.api

    if not hasattr(app, 'lifespan'):
        app.lifespan = tools_lifespan

    app.include_router(api.ansible_router, prefix="/api")
    app.include_router(api.platform_router, prefix="/api")
    app.include_router(api.task_router, prefix="/api")
    app.include_router(api.catalog_router, prefix="/api")
    
    app.include_router(api.tool_management_router, prefix="/api")
    app.include_router(tool_router, prefix="/tools")