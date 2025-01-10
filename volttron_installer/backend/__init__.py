from fastapi import FastAPI

from . import endpoints as api

def init(app: FastAPI):

    app.include_router(api.ansible_router, prefix="/api")
    app.include_router(api.platform_router, prefix="/api")
    app.include_router(api.task_router, prefix="/api")
