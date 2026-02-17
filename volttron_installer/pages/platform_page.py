import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.tiles import config_tile
from ..components.buttons import icon_button_wrapper
from ..components.header.header import header
from ..components.buttons.tile_icon import tile_icon
from ..navigation.state import NavigationState
from ..components.form_components import form_entry
from typing import Literal
from ..thin_endpoint_wrappers import *
from ..state import PlatformPageState as State
from ..models import Instance

from ..components.platform import (
    deployment_progress_dialog,
    pyenv_install_dialog,
    install_agent_dialog,
    remove_agent_dialog,
    platform_tabs,
    delete_platform_dialog
)

parts = Literal["connection", "instance_configuration"]

@rx.page(route="/platform/[uid]", on_load=State.on_platform_page_load)
def platform_page() -> rx.Component:

    # State.working_platform: Instance = State.platforms[State.current_uid]

    return rx.cond(
        State.is_hydrated, 
        rx.fragment(
            app_layout(
                header(
                    rx.hstack(
                        rx.link(
                            icon_button_wrapper.icon_button_wrapper(
                                tool_tip_content="Go back to instances",
                                icon_key="arrow-left",
                            ),
                            href="/instances",
                        ),
                        rx.text(f"""{
                                rx.cond(
                                    State.working_platform.new_instance,
                                    'New Platform',
                                    f'Platform: {State.platform_title}'
                                )
                            }""",
                            trim="both",
                            size="6"
                        ),
                        spacing="6",
                        align="center",
                    ),
                    rx.hstack(
                        rx.cond(
                            State.working_platform.new_instance==False,
                            icon_button_wrapper.icon_button_wrapper(
                                tool_tip_content="Copy Platform",
                                icon_key="copy",
                                on_click=State.copy_platform(State.current_uid)
                            )
                        ),
                        # Delete button opens dialog
                        icon_button_wrapper.icon_button_wrapper(
                            tool_tip_content="Delete platform",
                            icon_key="trash-2",
                            on_click=State.open_delete_dialog,
                        ),
                        # Delete Platform Dialog
                        delete_platform_dialog(),
                    ),
                    justify="between"
                ),
                platform_tabs()
            ),
            deployment_progress_dialog(),
            pyenv_install_dialog(),
            install_agent_dialog(),
            remove_agent_dialog(),
        ),
        # Skeleton Stuff
        rx.vstack(
            # Header
            rx.hstack(
                rx.hstack(
                    rx.skeleton(
                        rx.box(),
                        height="3rem",
                        width="5rem",
                        radius="5rem",
                        loading=True,
                    ),
                    rx.skeleton(
                        rx.box(),
                        height="3rem",
                        width="12rem",
                        radius="5rem",
                        loading=True,
                    ),
                    spacing="4",
                    align="center",
                ),
                rx.skeleton(
                    rx.box(),
                    height="3rem",
                    width="5rem",
                    radius="5rem",
                    loading=True,
                ),
                spacing="4",
                align="center",
                justify="between",
                width="100%",
            ),
            # Tabs divider
            rx.skeleton(
                rx.box(),
                width="100%",
                height="15px",
                loading=True,
            ),
            spacing="6",
            padding="1rem"
        )
    )

# General components
def agent_config_tile(text, left_component: rx.Component = False, right_component: rx.Component = False)->rx.Component:
    return rx.hstack(
        rx.cond(
            left_component,
            rx.flex(
                left_component,
                align="center",
                justify="center",
            )
        ),
        rx.flex(
            rx.text(text),
            class_name=f"agent_config_tile",
        ),
        rx.cond(
            right_component,
            rx.flex(        
                right_component,
                align="center",
                justify="center"
            )
        ),  
        spacing="2",
        align="center",
    )
