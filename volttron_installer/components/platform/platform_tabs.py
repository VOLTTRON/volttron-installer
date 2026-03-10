import reflex as rx
from ...state import PlatformPageState as State
from .status_tab import data_tab_content
from .configuration_tab import configuration_tab_content
from .logs_tab import logs_tab_content
from ...pages.drivers_tab_content import drivers_tab_content


def _nav_item(label: str, icon: str, value: str, disabled: bool | rx.Var = False) -> rx.Component:
    is_active = State.platform_nav == value
    return rx.box(
        rx.hstack(
            rx.icon(icon, size=18, flex_shrink="0"),
            rx.text(label, size="3", weight="medium"),
            spacing="3",
            align="center",
            width="100%",
        ),
        padding="0.6rem 1rem",
        border_radius="8px",
        cursor=rx.cond(disabled, "not-allowed", "pointer"),
        opacity=rx.cond(disabled, "0.4", "1"),
        background=rx.cond(
            is_active,
            "var(--accent-3)",
            "transparent",
        ),
        color=rx.cond(
            is_active,
            "var(--accent-11)",
            "var(--gray-11)",
        ),
        _hover=rx.cond(
            disabled,
            {},
            {"background": rx.cond(is_active, "var(--accent-3)", "var(--gray-3)")},
        ),
        on_click=rx.cond(disabled, rx.prevent_default, State.set_platform_nav(value)),
        width="100%",
        transition="background 0.15s, color 0.15s",
    )


def _sidebar() -> rx.Component:
    platform_locked = ~State.working_platform.platform.in_file
    return rx.vstack(
        # Platform label at top of sidebar
        rx.vstack(
            rx.text("Platform", size="2", color="var(--gray-9)", weight="bold", letter_spacing="0.08em"),
            rx.text(
                State.working_platform.platform.config.instance_name,
                size="4",
                weight="bold",
                color="var(--gray-12)",
                no_of_lines=1,
            ),
            spacing="1",
            align="start",
            padding="1rem 1rem 1.25rem 1rem",
            width="100%",
        ),
        rx.divider(margin="0"),
        # Main nav items
        rx.vstack(
            _nav_item("Overview", "monitor", "overview", disabled=platform_locked),
            _nav_item("Drivers", "cpu", "drivers", disabled=platform_locked),
            _nav_item("Logs", "scroll-text", "logs", disabled=platform_locked),
            spacing="1",
            align="start",
            width="100%",
            padding="0.75rem",
            flex="1",
        ),
        # Setup separated at the bottom
        rx.vstack(
            rx.divider(margin="0"),
            rx.vstack(
                _nav_item("Setup", "settings", "setup"),
                spacing="1",
                align="start",
                width="100%",
                padding="0.75rem",
            ),
            spacing="0",
            width="100%",
        ),
        spacing="0",
        align="start",
        width="240px",
        min_width="240px",
        height="100%",
        border_right="1px solid var(--gray-4)",
        background="var(--gray-1)",
    )


def _content_area() -> rx.Component:
    return rx.box(
        rx.match(
            State.platform_nav,
            ("overview", rx.box(data_tab_content(), on_mount=State.load_platform_status_background, width="100%")),
            ("setup", rx.box(configuration_tab_content(), padding="1.5rem", width="100%")),
            ("drivers", rx.box(drivers_tab_content(), on_mount=State.on_drivers_tab_mount, width="100%")),
            ("logs", rx.box(logs_tab_content(), padding="1.5rem", width="100%")),
            rx.box(data_tab_content(), width="100%"),
        ),
        flex="1",
        overflow_y="auto",
        height="100%",
    )


def platform_tabs() -> rx.Component:
    return rx.cond(
        State.is_hydrated,
        rx.box(
            rx.hstack(
                _sidebar(),
                _content_area(),
                spacing="0",
                align="start",
                width="100%",
                height="100%",
            ),
            width="100%",
            height="calc(100vh - 60px)",
            overflow="hidden",
        ),
    )

