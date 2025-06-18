"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config
from ..components.buttons import add_icon_button
from ..components import header
from ..components.form_components import form_entry
from ..components.tabs import platform_overview
from ..components.tiles.config_tile import config_tile
from ..components.buttons import tile_icon
from .platform_page import State as PlatformState 
from ..layouts.app_layout_sidebar import app_layout_sidebar

from ..state import IndexPageState


@rx.page(route="/")
def index() -> rx.Component:
    return app_layout_sidebar(
            platform_overview_tab()
        )

def platform_overview_tab() -> rx.Component:
    return rx.fragment(
        rx.vstack(
            header.header.header(
                rx.text("Overview", size="7"),
                add_icon_button.add_icon_button(
                    tool_tip_content="Create a Platform",
                    # on_click=rx.redirect("/platform/new")
                    on_click=lambda: PlatformState.generate_new_platform
                ),
                justify="between"
            ),
            platform_overview.platform_overview(),
        )
    )