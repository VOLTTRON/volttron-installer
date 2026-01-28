"""Welcome to Reflex! This file outlines the steps to create a basic app."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
import reflex as rx
import os
from rxconfig import config
from pprint import pprint
from .styles import styles
from .pages.index import index
from .pages.platform_new import new_platform_page
from .pages.platform_page import platform_page, State as PlatformState
from .pages.bacnet_scan import bacnet_scan_page

@asynccontextmanager
async def lifespan(app: FastAPI):
    #await flet_fastapi.app_manager.start()
    # Setup something at the loading of the application and
    # tear it down when the application is done.

    yield
    # Shut down of the tools
    from .backend.tool_manager import ToolManager
    ToolManager.stop_all_tools()
    #await flet_fastapi.app_manager.shutdown()




from .backend import init as init_backend

def api_transformer_func(api):
    """Transform the API to add custom FastAPI routers."""
    # If it's a Starlette app, we need to mount FastAPI routers differently
    # In v0.8.x, we need to use the raw ASGI app
    from fastapi import FastAPI
    if not isinstance(api, FastAPI):
        # Wrap or replace with FastAPI
        fastapi_app = FastAPI(lifespan=lifespan)
        init_backend(app=fastapi_app)
        # Mount the FastAPI app to the Starlette app without prefix since routers already have /api
        api.mount("", fastapi_app)
    else:
        init_backend(app=api)
    return api

# Create the fastapi app
#app = FastAPI(lifespan=lifespan)
#backend_app = FastAPI()
app = rx.App(
    style=styles.styles,
    api_transformer=api_transformer_func,
    theme=rx.theme(
        has_background=True,
        radius="medium",
        accent_color="blue",
    ),
    stylesheets=[
        "/custom.css",
    ],
)

# Register the lifespan task
app.register_lifespan_task(lifespan)