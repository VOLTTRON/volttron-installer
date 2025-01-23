"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config
from ..components.buttons import upload_button
from ..components.form_components import form_tab ,form_tile_column , form_view, form_entry
from ..components import configuring_components

from ..components.tabs import hosts_tab, config_store_templates, agent_setup, platform_overview
from ..volttron_installer_app import app
from ..components.tabs.state import PlatformOverviewState

class IndexTabState(rx.State):
    ...


def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.fragment(
        rx.vstack(
            rx.button("hehe click me", on_click=lambda: PlatformOverviewState.generate_new_platform),
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Hosts", value="tab_1"),
                    rx.tabs.trigger("Agent Setup", value="tab_2"),
                    rx.tabs.trigger("Platforms", value="tab_3"),
                    rx.tabs.trigger("Config Store Templates", value="tab_4"),
                ),
                rx.tabs.content(
                    hosts_tab.host_tab(),
                    value="tab_1"
                ),
                rx.tabs.content(
                    agent_setup.agent_setup_tab(),
                    value="tab_2"
                ),
                rx.tabs.content(
                    platform_overview.platform_overview(),
                    value="tab_3"
                ),

                rx.tabs.content(
                    config_store_templates.config_store_templates_tab(),
                    value="tab_4"
                ),
                default_value="tab_1"
            )
        )
    )
