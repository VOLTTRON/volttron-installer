"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config
from ..components.buttons import upload_button
from ..components.form_components import form_tab ,form_tile_column , form_view, form_entry
from ..styles import styles
from ..components import configuring_components

from ..components.configuring_components.hosts import HostState
from ..components.configuring_components.hosts import host_instance
from ..volttron_installer_app import app


class State(rx.State):
    """The app state."""

    ...


def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.fragment(
        rx.vstack(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Hosts", value="tab_1"),
                    rx.tabs.trigger("Agent Setup", value="tab_2"),
                    rx.tabs.trigger("Platforms", value="tab_3"),
                    rx.tabs.trigger("Config Store Templates", value="tab_4"),
                ),
                rx.tabs.content(
                    form_tab.form_tab(
                        form_tile_column.form_tile_column_wrapper(
                            rx.button("Setup a Host")
                        ),
                        host_instance()
                    ),
                    value="tab_1"
                ),
                rx.tabs.content(
                    form_tab.form_tab(
                        form_tile_column.form_tile_column_wrapper(
                            rx.button("Setup an Agent")
                        ),
                        configuring_components.agent_setup.agent_setup_instance()
                    ),
                    value="tab_2"
                ),
                rx.tabs.content(
                    form_tab.form_tab(
                        form_tile_column.form_tile_column_wrapper(
                            rx.button("Setup a Host")
                        ),
                        rx.button("pls save me")
                        # configuring_components.hosts.host_instance()
                    ),
                    value="tab_3"
                ),

                rx.tabs.content(
                    form_tab.form_tab(
                        form_tile_column.form_tile_column_wrapper(
                            rx.button("Setup an Template")
                        ),
                        configuring_components.config_templates_instance()
                    ),
                    value="tab_4"
                ),
                default_value="tab_1"
            )
        )
    )
