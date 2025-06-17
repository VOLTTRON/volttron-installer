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

from ..state import IndexPageState


@rx.page(route="/")
def index() -> rx.Component:
    return rx.fragment(
        rx.vstack(
            header.header.header(
                rx.text("VOLTTRON Installer", size="7"),
                justify="between"
            ),
            rx.vstack(
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("Platform Overview", value="1"),
                        rx.tabs.trigger("Tools", value="2"),
                    ),
                    rx.tabs.content(
                        platform_overview_tab(),
                        value="1",
                    ),
                    rx.tabs.content(
                        tools_tab(),
                        value="2",
                    ),
                    default_value="1",
                ),
                width="100%",
            ),
            width="100%",
        )
    )

def bacnet_scan_tab() -> rx.Component:
    return rx.fragment(
        rx.vstack(
            form_entry.form_entry(
                "IP Address",
                rx.hstack(
                    rx.input(),
                    rx.button(
                        rx.cond(
                            IndexPageState.proxy_up,
                            "Stop Proxy",
                            "Start Proxy",
                        ),
                        loading=IndexPageState.is_starting_proxy,
                        color_scheme=rx.cond(
                            IndexPageState.proxy_up,
                            "red",
                            "primary"
                        ),
                        on_click=lambda: IndexPageState.toggle_proxy()
                    )
                ),
            ),
            justify="center",
            width="100%",
        )
    )

def tools_tab() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                config_tile(
                    "BACnet Scan",
                    right_component=tile_icon.tile_icon(
                        "chevron-right",
                        on_click=lambda: IndexPageState.set_selected_tool("bacnet_scan"),
                        class_name=rx.cond(
                            IndexPageState.selected_tool == "bacnet_scan",
                            "icon_button active",
                            "icon_button"
                        )
                    )
                )
            ),
            rx.vstack(
                # Conditionally rendered depending on what "mode" we're in
                rx.cond(
                    # Base case, if no tool is selected
                    IndexPageState.selected_tool == "",
                    rx.box(),
                    rx.cond(
                        IndexPageState.selected_tool == "bacnet_scan",
                        bacnet_scan_tab(),
                        
                        # TODO implement future tools following this format
                        # rx.cond(
                            
                        # )
                    )
                ),
                padding_left="2rem",
            ),
            padding_left="1rem",
            padding_right="1rem",
        ),
        width="100%",
        padding_top="1rem"
    )

def platform_overview_tab() -> rx.Component:
    return rx.fragment(
        rx.vstack(
            header.header.header(
                rx.text("Overview", size="5"),
                add_icon_button.add_icon_button(
                    tool_tip_content="Create a Platform",
                    # on_click=rx.redirect("/platform/new")
                    size=20,
                    on_click=lambda: PlatformState.generate_new_platform
                ),
                justify="between"
            ),
            platform_overview.platform_overview(),
        )
    )