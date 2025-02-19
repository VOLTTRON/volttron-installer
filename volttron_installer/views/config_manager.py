from flet import AppBar, ElevatedButton, Page, Text, View, colors

from typing import Callable

import logging

_log = logging.getLogger(__name__)


def config_manager_view(page: Page, message: str) -> View:
    from volttron_installer.views import InstallerViews as vi_views

    return View("/", [
        AppBar(title=Text(f"Choose Application: {message}"),
               automatically_imply_leading=False,
               bgcolor=colors.SURFACE_VARIANT),
        ElevatedButton("Platform Manager",
                       on_click=lambda _: page.go(vi_views.platform_manager.route)),
    ])
