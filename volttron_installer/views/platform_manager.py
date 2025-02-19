from flet import AppBar, ElevatedButton, Page, Text, View, colors

from typing import Callable

import logging

_log = logging.getLogger(__name__)


def platform_manager_view(page: Page) -> View:
    from volttron_installer.views import InstallerViews as vi_views

    return View(vi_views.platform_manager.route, [
        AppBar(title=Text("Platform Manager!"),
               automatically_imply_leading=False,
               bgcolor=colors.SURFACE_VARIANT),
        ElevatedButton("Configuration Manager",
                       on_click=lambda _: page.go(vi_views.config_manager.route)),
    ])
