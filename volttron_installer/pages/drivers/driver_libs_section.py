"""Driver library listing section."""

import reflex as rx
from ...state import PlatformPageState as State


def _installed_driver_card(driver: dict) -> rx.Component:
    """Card for a single installed driver library."""
    return rx.card(
        rx.hstack(
            rx.center(
                rx.icon("package-check", size=18, color="var(--green-9)"),
                width="30px",
                height="30px",
                border_radius="8px",
                background="var(--green-3)",
            ),
            rx.vstack(
                rx.text(driver["name"], weight="bold", size="3"),
                rx.text(f"Version {driver['version']}", size="1", color="gray"),
                spacing="1",
                align_items="start",
                flex="1",
            ),
            rx.button(
                rx.icon("settings", size=14),
                "Configure",
                size="1",
                variant="soft",
                on_click=State.open_configure_driver_dialog(driver["name"]),
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        width="100%",
        variant="surface",
        _hover={"background": "var(--gray-2)"},
    )


def _summary_stat(label: str, value: rx.Var | str, icon: str) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.center(
                rx.icon(icon, size=18, color="var(--accent-10)"),
                width="34px",
                height="34px",
                border_radius="9px",
                background="var(--accent-3)",
            ),
            rx.vstack(
                rx.text(label, size="1", color="gray", weight="medium"),
                rx.text(value, size="5", weight="bold"),
                spacing="0",
                align_items="start",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        width="100%",
        variant="surface",
    )


def installed_driver_libs_section() -> rx.Component:
    """Section showing installed driver libraries."""
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("Installed Driver Libraries", size="4", weight="bold"),
                rx.text(
                    "Libraries available in this platform's virtual environment.",
                    size="1",
                    color="gray",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=14),
                "Refresh",
                on_click=State.fetch_installed_driver_libs,
                size="1",
                variant="ghost",
                color_scheme="gray",
                loading=State.loading_installed_drivers,
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        rx.cond(
            State.loading_installed_drivers,
            rx.center(
                rx.hstack(
                    rx.spinner(size="2"),
                    rx.text("Scanning venv…", size="2", color="gray"),
                    spacing="2",
                    align="center",
                ),
                padding="1rem",
                width="100%",
            ),
            rx.cond(
                State.installed_driver_libs.length() > 0,
                rx.box(
                    rx.vstack(
                    rx.foreach(
                        State.installed_driver_libs,
                        _installed_driver_card,
                    ),
                        spacing="2",
                        width="100%",
                    ),
                    max_height="320px",
                    overflow_y="auto",
                    width="100%",
                ),
                rx.callout(
                    rx.text(
                        "No driver libraries installed yet. Use Install Driver Library to add your first driver package.",
                        size="2",
                    ),
                    icon="info",
                    color_scheme="gray",
                ),
            ),
        ),
        spacing="3",
        width="100%",
    )