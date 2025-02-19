"""Welcome to Reflex! This file outlines the steps to create a basic app."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
import reflex as rx
import os
from rxconfig import config
from pprint import pprint
from .frontend.styles import styles
# from .frontend.frontend.pages import index

@asynccontextmanager
async def lifespan(app: FastAPI):
    #await flet_fastapi.app_manager.start()
    # Setup something at the loading of the application and
    # tear it down when the application is done.

    yield
    #await flet_fastapi.app_manager.shutdown()


# Create the fastapi app
#app = FastAPI(lifespan=lifespan)
#backend_app = FastAPI()
app = rx.App(
    style=styles.styles
    )

# app.add_page(index)

# Register the lifespan task
app.register_lifespan_task(lifespan)

from .backend import init as init_backend

# Mount the backend app to the fastapi app.  More than one endpoint can be mounted to the same fastapi app.
init_backend(app=app)

