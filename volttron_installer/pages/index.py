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
                        rx.icon("check-circle", size=16, color="green"),
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

def home_page() -> rx.Component:
    """Home page content - Docker Desktop style"""
    return rx.vstack(
        rx.text("Home", size="7", weight="bold"),
        # Main content area with two columns
        rx.hstack(
            # Left column - Featured section
            rx.vstack(
                rx.heading("Featured", size="5", weight="bold", margin_bottom="1rem"),
                # Run your first instance card
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("circle-play", size=24, color=rx.color("accent")),
                            rx.heading("Run Your First Instance", size="4", weight="bold"),
                            spacing="2",
                            align="center",
                        ),
                        rx.text(
                            "Get started with VOLTTRON by creating and deploying your first instance.",
                            size="2",
                            color="gray",
                        ),
                        rx.button(
                            rx.icon("plus", size=16),
                            "Create Instance",
                            on_click=PlatformPageState.show_create_platform_options,
                            size="2",
                            variant="solid",
                        ),
                        spacing="3",
                        align_items="start",
                    ),
                    width="100%",
                ),
                width="55%",
                align_items="start",
                align="start",
            ),
            # Right column - Get Started and Useful Links
            rx.vstack(
                # Get Started section
                rx.vstack(
                    rx.heading("Get Started", size="5", weight="bold", margin_bottom="0.75rem"),
                    rx.link(
                        rx.text("Run a VOLTTRON Instance", size="2", color=rx.color("accent")),
                        href="/instances",
                    ),
                    rx.link(
                        rx.text("VOLTTRON Documentation", size="2", color=rx.color("accent")),
                        href="https://volttron.readthedocs.io/en/main/",
                        is_external=True,
                    ),
                    rx.link(
                        rx.text("VOLTTRON Core (Modular)", size="2", color=rx.color("accent")),
                        href="https://github.com/eclipse-volttron/volttron-core",
                        is_external=True,
                    ),
                    spacing="2",
                    align_items="start",
                    width="100%",
                ),
                # Useful Links section
                rx.vstack(
                    rx.heading("Useful Links", size="5", weight="bold", margin_bottom="0.75rem", margin_top="2rem"),
                    rx.link(
                        rx.text("VOLTTRON Installer (GitHub)", size="2", color=rx.color("accent")),
                        href="https://github.com/VOLTTRON/volttron-installer",
                        is_external=True,
                    ),
                    rx.link(
                        rx.text("VOLTTRON Monolithic", size="2", color=rx.color("accent")),
                        href="https://github.com/VOLTTRON/volttron",
                        is_external=True,
                    ),
                    rx.link(
                        rx.text("Eclipse VOLTTRON", size="2", color=rx.color("accent")),
                        href="https://github.com/eclipse-volttron",
                        is_external=True,
                    ),
                    spacing="2",
                    align_items="start",
                    width="100%",
                ),
                width="25%",
                align_items="start",
            ),
            spacing="6",
            align_items="start",
            justify="between",
            width="100%",
        ),
        # Create Platform Dialog
        create_platform_dialog(),
        padding="2rem",
        overflow_y="auto",
        height="100%",
        width="100%",
        spacing="3",
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