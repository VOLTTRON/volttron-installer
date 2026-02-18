import reflex as rx
from ...state import PlatformPageState as State
from .status_tab import data_tab_content
from .configuration_tab import configuration_tab_content
from .logs_tab import logs_tab_content
from ...pages.drivers_tab_content import drivers_tab_content

def platform_tabs() -> rx.Component:
    # State.working_platform: Instance = State.platforms[State.current_uid]
    return rx.cond(
        State.is_hydrated,
        rx.box(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        "Status", value="status", disabled=rx.cond(
                            State.working_platform.platform.in_file,
                            False,
                            True
                        )
                    ),
                    rx.tabs.trigger("Configuration", value="configuration"),
                    rx.tabs.trigger(
                        "Drivers", value="drivers", disabled=rx.cond(
                            State.working_platform.platform.in_file,
                            False,
                            True
                        )
                    ),
                    rx.tabs.trigger(
                        "Logs", value="logs", disabled=rx.cond(
                            State.working_platform.platform.in_file,
                            False,
                            True
                        )
                    ),
                ),
                rx.tabs.content(
                    rx.box(
                        data_tab_content(),
                        on_mount=State.load_platform_status_background,
                    ),
                    value="status"
                ),
                rx.tabs.content(
                    rx.box(
                        configuration_tab_content(),
                        padding="1rem"
                    ),
                    value="configuration"
                ),
                rx.tabs.content(
                    rx.box(
                        drivers_tab_content(),
                    ),
                    value="drivers"
                ),
                rx.tabs.content(
                    rx.box(
                        logs_tab_content(),
                        padding="1rem"
                    ),
                    value="logs"
                ),
                default_value=rx.cond(
                    State.working_platform.platform.in_file,
                    "status",
                    "configuration"
                )
            )
        )
    )
