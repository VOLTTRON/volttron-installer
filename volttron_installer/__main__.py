import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import flet as ft
import flet.fastapi as flet_fastapi
from fastapi import FastAPI, Request
from flet import Page, RouteChangeEvent
from volttron_installer.modules.global_event_bus import global_event_bus
from starlette.responses import RedirectResponse
from flet import AppBar, Dropdown, ElevatedButton, Page, Text, View, colors, RouteChangeEvent

from .settings import get_settings

settings = get_settings()

logging.basicConfig(level=logging.getLevelName(settings.log_level))
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("flet_core").setLevel(logging.WARNING)
logging.getLogger("flet.fastapi").setLevel(logging.WARNING)

_log = logging.getLogger(__name__)

os.environ["FLET_SECRET_KEY"] = settings.secret_key


async def main(page: Page):
    from volttron_installer.views import InstallerViews as vi_views
    from volttron_installer.modules.dynamic_routes import dynamic_routes
    page.theme_mode="dark"

    try:
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.title = settings.app_name

        def route_change(e: RouteChangeEvent):
            page.views.clear()

            # First check static routes
            found = False
            for p in vi_views:
                if p.route == e.route:
                    page.views.append(p.instance(page=page))
                    found = True
                    break

            if not found:
                return

            # If not found, check dynamic routes
            if not found:
                page.views.append(dynamic_routes[e.route])
                found = True

            if not found:
                raise ValueError(f"The route {e.route} was not defined.")

            # If we are on the home page, publish a signal to refresh all the
            # form tiles.
            if page.route == "/":
                global_event_bus.publish("tab_change")

            page.update()

        def view_pop(view):
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route)

        page.on_route_change = route_change
        page.on_view_pop = view_pop
        page.go(page.route)

    except Exception as e:
        _log.exception(e)


# Hook flet into FastAPI using flet.fastapi module
@asynccontextmanager
async def lifespan(app: FastAPI):
    await flet_fastapi.app_manager.start()
    yield
    await flet_fastapi.app_manager.shutdown()


# Create the fastapi app
app = FastAPI(lifespan=lifespan)
#backend_app = FastAPI()

from .backend import init as init_backend

init_backend(app)
# Mount the backend app to the fastapi app.  More than one endpoint can be mounted to the same fastapi app.
#app.mount("/backend", backend_app)

# Mount the flet app to the fastapi app.  More than one endpoint can be mounted to the same fastapi app.
app.mount(
    "/ui",
    flet_fastapi.app(main,
                     web_renderer=ft.WebRenderer.AUTO,
                     upload_dir="volttron_installer/uploaded_configs")
                    #  upload_dir=Path(
                    #      settings.upload_dir).expanduser().as_posix()))
                    )


@app.get("/")
async def index(request: Request):
    return RedirectResponse(url="/ui")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run("volttron_installer.__main__:app", reload=True)
