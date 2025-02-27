import reflex as rx
from fastapi import FastAPI

from . import endpoints as api

def init(app: FastAPI | rx.App):

    # Reflex wrapps around the fastapi endpoint so we need to modifiy the app object
    # in order to add routes to it.
    if isinstance(app, rx.App):
        app = app.api

    app.include_router(api.ansible_router, prefix="/api")
    app.include_router(api.platform_router, prefix="/api")
    app.include_router(api.task_router, prefix="/api")
    app.include_router(api.catalog_router, prefix="/api")
