"""Drivers tab content — main composition module."""

import reflex as rx
from ...state import PlatformPageState as State
from .driver_libs_section import installed_driver_libs_section, _summary_stat
from .driver_config_store import platform_driver_config_section
from .driver_dialogs import (
    add_driver_dialog,
    edit_driver_dialog,
    delete_driver_dialog,
    delete_live_config_dialog,
    live_config_edit_dialog,
)
from .driver_install_dialogs import (
    install_driver_lib_dialog,
    configure_driver_dialog,
)


def driver_card(driver: dict) -> rx.Component:
    """Display card for a single driver configuration"""
    return rx.card(
        rx.vstack(
            # Header row with path and actions
            rx.hstack(
                rx.vstack(
                    rx.text(
                        rx.code(f"{driver['campus']}/{driver['building']}/{driver['unit']}"),
                        weight="bold",
                        size="4",
                    ),
                    rx.hstack(
                        rx.badge(
                            driver["driver_type"],
                            variant="soft",
                            color_scheme="blue",
                        ),
                        rx.text(
                            f"Interval: {driver['interval']}s",
                            size="2",
                            color="gray",
                        ),
                        spacing="2",
                    ),
                    spacing="1",
                    align_items="start",
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("pencil", size=16),
                        on_click=lambda: State.open_edit_driver_dialog(driver["path"]),
                        size="2",
                        variant="soft",
                        color_scheme="gray",
                    ),
                    rx.button(
                        rx.icon("trash-2", size=16),
                        on_click=lambda: State.open_delete_driver_dialog(
                            driver["path"], driver["config_id"]
                        ),
                        size="2",
                        variant="soft",
                        color_scheme="red",
                    ),
                    spacing="2",
                ),
                justify="between",
                width="100%",
                align="center",
            ),

            # Details row
            rx.divider(),
            rx.hstack(
                rx.vstack(
                    rx.text("Registry", size="1", color="gray", weight="medium"),
                    rx.text(driver["registry"], size="2"),
                    spacing="1",
                    align_items="start",
                ),
                rx.vstack(
                    rx.text("Timezone", size="1", color="gray", weight="medium"),
                    rx.text(driver["timezone"], size="2"),
                    spacing="1",
                    align_items="start",
                ),
                rx.cond(
                    driver.get("heart_beat_point", "") != "",
                    rx.vstack(
                        rx.text("Heartbeat Point", size="1", color="gray", weight="medium"),
                        rx.text(driver.get("heart_beat_point", ""), size="2"),
                        spacing="1",
                        align_items="start",
                    ),
                ),
                spacing="6",
                wrap="wrap",
            ),

            spacing="3",
            width="100%",
        ),
        width="100%",
    )


def drivers_tab_content() -> rx.Component:
    """Main drivers tab content with clearer IA and better space usage."""
    return rx.vstack(
        # Header + primary actions
        rx.hstack(
            rx.vstack(
                rx.heading("Drivers Workspace", size="6"),
                rx.text(
                    "Manage driver libraries and live config keys from one place.",
                    size="2",
                    color="gray",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("refresh-cw", size=14),
                    "Refresh All",
                    on_click=[State.fetch_installed_driver_libs, State.fetch_vctl_config_list],
                    size="2",
                    variant="soft",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.icon("package-plus"),
                    "Install Driver Library",
                    on_click=State.open_install_driver_lib_dialog,
                    size="2",
                    variant="solid",
                    color_scheme="purple",
                ),
                spacing="2",
                align="center",
            ),
            align="end",
            justify="between",
            width="100%",
            spacing="4",
        ),

        # Snapshot stats
        rx.grid(
            _summary_stat("Installed Libraries", State.installed_driver_libs.length(), "package-check"),
            _summary_stat("Config Agents", State.vctl_config_agents.length(), "layers"),
            _summary_stat("Config Entries", State.config_tree_rows.length(), "file-text"),
            columns="3",
            spacing="3",
            width="100%",
        ),

        # Main workspace
        rx.grid(
            rx.card(
                installed_driver_libs_section(),
                width="100%",
                height="100%",
                padding="1rem",
            ),
            rx.card(
                platform_driver_config_section(),
                width="100%",
                height="100%",
                padding="1rem",
            ),
            columns="2",
            spacing="3",
            width="100%",
        ),

        # Dialogs
        add_driver_dialog(),
        edit_driver_dialog(),
        delete_driver_dialog(),
        install_driver_lib_dialog(),
        configure_driver_dialog(),
        delete_live_config_dialog(),
        live_config_edit_dialog(),

        spacing="4",
        width="100%",
        padding="1.25rem",
    )