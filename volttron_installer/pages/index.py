"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config
from ..components.buttons import add_icon_button
from ..components import header

from ..components.tabs import platform_overview
from .platform_page import State as PlatformState 

class IndexTabState(rx.State):
    ...

@rx.page(route="/")
def index() -> rx.Component:
    # Welcome Page (Index)
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
