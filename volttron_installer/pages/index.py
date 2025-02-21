"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config
from ..components.buttons import add_icon_button
# from ..components.form_components import form_tab ,form_tile_column , form_view, form_entry
from ..components import configuring_components, header
# from ..components.tabs.host_tab import hosts_tab

from ..components.tabs import config_store_templates, agent_setupa, platform_overview
# from ..components.tabs.state import PlatformOverviewState
from .platform_page import State as PlatformState 

class IndexTabState(rx.State):
    ...

@rx.page(route="/")
def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.fragment(
        rx.vstack(
            header.header.header(
                rx.text("Overview", size="5"),
                add_icon_button.add_icon_button(
                    tool_tip_content="Create a Platform",
                    on_click=lambda: PlatformState.generate_new_platform
                ),
                justify="between"
            ),
            platform_overview.platform_overview(),
        )
    )
