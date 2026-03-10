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

from ..state import IndexPageState, PlatformPageState


def create_platform_dialog() -> rx.Component:
    """Dialog for choosing between Deploy New or Connect to Existing"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.cond(
                    PlatformPageState.connect_existing_mode,
                    "Connect to Existing VOLTTRON",
                    "Create Platform"
                )
            ),
            ssh_setup_instructions(),
            rx.cond(
                PlatformPageState.connect_existing_mode,
                # Connect to Existing flow
                connect_existing_form(),
                # Mode selection
                mode_selection(),
            ),
            max_width="500px",
        ),
        open=PlatformPageState.show_create_platform_dialog,
    )


def ssh_setup_instructions() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("SSH setup (run locally before continuing)", weight="medium"),
            rx.text(
                "1) Create an SSH key if you do not have one:",
                size="1",
                color="gray",
            ),
            rx.code("ssh-keygen -t ed25519 -C \"volttron-installer\"", size="1"),
            rx.text(
                "2) Copy your public key to the remote host:",
                size="1",
                color="gray",
            ),
            rx.code("ssh-copy-id -p 22 <user>@<host>", size="1"),
            rx.text(
                "Replace <user> and <host> below.",
                size="1",
                color="gray",
            ),
            spacing="2",
            align_items="start",
        ),
        width="100%",
    )


def mode_selection() -> rx.Component:
    """Initial mode selection: Deploy New or Connect Existing"""
    return rx.vstack(
        rx.text(
            "Choose how you want to add a VOLTTRON platform:",
            size="2",
            color="gray",
        ),
        rx.vstack(
            # Deploy New option
            rx.card(
                rx.hstack(
                    rx.icon("rocket", size=32, color="var(--accent-9)"),
                    rx.vstack(
                        rx.text("Deploy New Instance", weight="bold"),
                        rx.text(
                            "Install and configure a fresh VOLTTRON instance on a remote machine",
                            size="1",
                            color="gray",
                        ),
                        align_items="start",
                        spacing="1",
                    ),
                    spacing="4",
                    align="center",
                    width="100%",
                ),
                on_click=PlatformPageState.generate_new_platform,
                cursor="pointer",
                _hover={"background": "var(--gray-3)"},
                width="100%",
            ),
            # Connect Existing option
            rx.card(
                rx.hstack(
                    rx.icon("link", size=32, color="var(--accent-9)"),
                    rx.vstack(
                        rx.text("Connect to Existing", weight="bold"),
                        rx.text(
                            "Connect to a VOLTTRON instance that's already installed on a remote machine",
                            size="1",
                            color="gray",
                        ),
                        align_items="start",
                        spacing="1",
                    ),
                    spacing="4",
                    align="center",
                    width="100%",
                ),
                on_click=PlatformPageState.switch_to_connect_existing,
                cursor="pointer",
                _hover={"background": "var(--gray-3)"},
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        rx.hstack(
            rx.dialog.close(
                rx.button(
                    "Cancel",
                    variant="soft",
                    color_scheme="gray",
                    on_click=PlatformPageState.close_create_platform_dialog,
                ),
            ),
            justify="end",
            width="100%",
            padding_top="1rem",
        ),
        spacing="4",
        width="100%",
        padding="1rem",
    )


def connect_existing_form() -> rx.Component:
    """Form for connecting to an existing VOLTTRON instance"""
    return rx.vstack(
        rx.text(
            "Enter the SSH connection details for the machine with VOLTTRON installed:",
            size="2",
            color="gray",
        ),
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text("SSH Host", size="2", weight="medium"),
                    rx.input(
                        placeholder="192.168.1.100 or hostname",
                        value=PlatformPageState.connect_ssh_host,
                        on_change=PlatformPageState.set_connect_ssh_host,
                        width="100%",
                    ),
                    width="70%",
                ),
                rx.vstack(
                    rx.text("Port", size="2", weight="medium"),
                    rx.input(
                        placeholder="22",
                        value=PlatformPageState.connect_ssh_port,
                        on_change=PlatformPageState.set_connect_ssh_port,
                        width="100%",
                    ),
                    width="30%",
                ),
                spacing="3",
                width="100%",
            ),
            rx.vstack(
                rx.text("SSH User", size="2", weight="medium"),
                rx.input(
                    placeholder="username",
                    value=PlatformPageState.connect_ssh_user,
                    on_change=PlatformPageState.set_connect_ssh_user,
                    width="100%",
                ),
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        # Detection results
        rx.cond(
            PlatformPageState.detected_volttron_home != "",
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("check", size=16, color="green"),
                        rx.text("Detected VOLTTRON Installation", weight="medium"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text("VOLTTRON_HOME:", size="1", color="gray"),
                        rx.code(PlatformPageState.detected_volttron_home, size="1"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text("venv:", size="1", color="gray"),
                        rx.code(PlatformPageState.detected_volttron_venv, size="1"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text("Status:", size="1", color="gray"),
                        rx.cond(
                            PlatformPageState.detected_volttron_running,
                            rx.badge("Running", color_scheme="green"),
                            rx.badge("Stopped", color_scheme="orange"),
                        ),
                        spacing="2",
                    ),
                    spacing="2",
                    align_items="start",
                ),
                width="100%",
            ),
            rx.fragment(),
        ),
        rx.hstack(
            rx.button(
                rx.icon("arrow-left", size=16),
                "Back",
                variant="soft",
                color_scheme="gray",
                on_click=PlatformPageState.switch_to_deploy_new,
            ),
            rx.spacer(),
            rx.button(
                rx.icon("search", size=16),
                "Detect",
                variant="soft",
                on_click=PlatformPageState.detect_existing_volttron,
                loading=PlatformPageState.detecting_volttron,
            ),
            rx.dialog.close(
                rx.button(
                    "Connect",
                    on_click=PlatformPageState.connect_to_existing_platform,
                ),
            ),
            spacing="2",
            width="100%",
            padding_top="1rem",
        ),
        spacing="4",
        width="100%",
        padding="1rem",
    )


@rx.page(route="/", on_load=PlatformState.hydrate_state)
def index() -> rx.Component:
    """Home page with Get Started section"""
    return app_layout_sidebar(
            home_page()
        )

@rx.page(route="/instances", on_load=PlatformState.hydrate_state)
def instances() -> rx.Component:
    """Instances page showing all VOLTTRON platforms"""
    return app_layout_sidebar(
            instances_tab()
        )

def _instance_card(instance) -> rx.Component:
    """Compact card for a single instance on the home dashboard."""
    is_deployed = instance.deployed
    return rx.card(
        rx.hstack(
            rx.box(
                width="8px",
                height="8px",
                border_radius="50%",
                flex_shrink="0",
                background=rx.cond(is_deployed, "var(--green-9)", "var(--gray-6)"),
                margin_top="3px",
            ),
            rx.vstack(
                rx.link(
                    rx.text(instance.platform.config.instance_name, weight="medium", size="2"),
                    href=rx.cond(
                        is_deployed,
                        f"/platform/{instance.platform.config.instance_name}",
                        f"/platform/{instance.platform.config.instance_name}",
                    ),
                    color="inherit",
                    text_decoration="none",
                ),
                rx.hstack(
                    rx.badge(
                        rx.cond(is_deployed, "Deployed", "Not Deployed"),
                        color_scheme=rx.cond(is_deployed, "green", "gray"),
                        variant="soft",
                        size="1",
                    ),
                    rx.text(
                        rx.cond(
                            instance.host.ansible_connection == "local",
                            "Local",
                            instance.host.ansible_host,
                        ),
                        size="1",
                        color="var(--gray-9)",
                    ),
                    spacing="2",
                    align="center",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.link(
                rx.icon("arrow-right", size=14, color="var(--gray-9)"),
                href=f"/platform/{instance.platform.config.instance_name}",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
        _hover={"background": "var(--gray-2)"},
    )


def _home_empty_state() -> rx.Component:
    """Shown when no instances exist yet."""
    return rx.vstack(
        rx.vstack(
            rx.icon("server", size=48, color="var(--gray-7)"),
            rx.heading("Set up your first instance", size="5", weight="bold"),
            rx.text(
                "Deploy a new VOLTTRON platform or connect to an existing one to get started.",
                size="2",
                color="var(--gray-10)",
                text_align="center",
                max_width="380px",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("rocket", size=15),
                    "Deploy New Instance",
                    on_click=PlatformPageState.generate_new_platform,
                    size="2",
                ),
                rx.button(
                    rx.icon("link", size=15),
                    "Connect Existing",
                    variant="soft",
                    color_scheme="gray",
                    on_click=PlatformPageState.switch_to_connect_existing,
                    size="2",
                ),
                spacing="3",
            ),
            spacing="4",
            align="center",
        ),
        align="center",
        justify="center",
        width="100%",
        padding_y="6rem",
    )


def _home_dashboard() -> rx.Component:
    """Shown when at least one instance exists."""
    return rx.vstack(
        # Stats row
        rx.hstack(
            rx.card(
                rx.vstack(
                    rx.text("Total Instances", size="1", color="var(--gray-9)", weight="medium"),
                    rx.text(PlatformPageState.total_instance_count, size="7", weight="bold"),
                    spacing="1",
                    align_items="start",
                ),
                width="180px",
            ),
            rx.card(
                rx.vstack(
                    rx.text("Deployed", size="1", color="var(--gray-9)", weight="medium"),
                    rx.hstack(
                        rx.text(PlatformPageState.deployed_instance_count, size="7", weight="bold", color="var(--green-10)"),
                        spacing="2",
                        align="end",
                    ),
                    spacing="1",
                    align_items="start",
                ),
                width="180px",
            ),
            spacing="4",
        ),
        # Two-column layout: instances list + links
        rx.hstack(
            # Instances list
            rx.vstack(
                rx.hstack(
                    rx.heading("Instances", size="4", weight="bold"),
                    rx.spacer(),
                    rx.button(
                        rx.icon("plus", size=14),
                        "Add",
                        size="1",
                        variant="soft",
                        on_click=PlatformPageState.show_create_platform_options,
                    ),
                    width="100%",
                    align="center",
                ),
                rx.foreach(
                    PlatformPageState.in_file_platforms,
                    _instance_card,
                ),
                rx.link(
                    rx.hstack(
                        rx.text("View all instances", size="2", color="var(--accent-9)"),
                        rx.icon("arrow-right", size=13, color="var(--accent-9)"),
                        spacing="1",
                        align="center",
                    ),
                    href="/instances",
                ),
                spacing="3",
                align_items="start",
                width="100%",
            ),
            # Links sidebar
            rx.vstack(
                rx.vstack(
                    rx.heading("Quick Links", size="4", weight="bold"),
                    rx.link(
                        rx.text("VOLTTRON Documentation", size="2", color="var(--accent-9)"),
                        href="https://volttron.readthedocs.io/en/main/",
                        is_external=True,
                    ),
                    rx.link(
                        rx.text("Eclipse VOLTTRON (GitHub)", size="2", color="var(--accent-9)"),
                        href="https://github.com/eclipse-volttron",
                        is_external=True,
                    ),
                    rx.link(
                        rx.text("VOLTTRON Core (Modular)", size="2", color="var(--accent-9)"),
                        href="https://github.com/eclipse-volttron/volttron-core",
                        is_external=True,
                    ),
                    rx.link(
                        rx.text("VOLTTRON Monolithic", size="2", color="var(--accent-9)"),
                        href="https://github.com/VOLTTRON/volttron",
                        is_external=True,
                    ),
                    rx.link(
                        rx.text("VOLTTRON Installer (GitHub)", size="2", color="var(--accent-9)"),
                        href="https://github.com/VOLTTRON/volttron-installer",
                        is_external=True,
                    ),
                    spacing="2",
                    align_items="start",
                    width="100%",
                ),
                width="220px",
                min_width="220px",
                flex_shrink="0",
                align_items="start",
            ),
            spacing="8",
            align_items="start",
            width="100%",
        ),
        spacing="5",
        align_items="start",
        width="100%",
    )


def home_page() -> rx.Component:
    """Home page content — adapts based on whether instances exist."""
    return rx.vstack(
        rx.text("Home", size="7", weight="bold"),
        rx.cond(
            PlatformPageState.has_any_instance,
            _home_dashboard(),
            _home_empty_state(),
        ),
        # Dialog always rendered so events can open it
        create_platform_dialog(),
        padding="2rem",
        overflow_y="auto",
        height="100%",
        width="100%",
        spacing="4",
        align_items="start",
    )

def instances_tab() -> rx.Component:
    return rx.fragment(
        rx.vstack(
            header.header.header(
                rx.text("Instances", size="7", weight="bold"),
                add_icon_button.add_icon_button(
                    tool_tip_content="Create a Platform",
                    on_click=PlatformPageState.show_create_platform_options
                ),
                justify="between"
            ),
            # Create Platform Dialog
            create_platform_dialog(),
            platform_overview.platform_overview(),
            overflow_y="auto",
            height="100%",
            width="100%",
        )
    )