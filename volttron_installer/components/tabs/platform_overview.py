import typing
import reflex as rx 
from .state import PlatformOverviewState 
from ...pages.platform_page import State as PlatformState, Instance
from ..tiles.platform_tile import platform_tile
from ...navigation.state import NavigationState

def craft_new_platform_tile(platform_entry: Instance) -> rx.Component:
    return rx.context_menu.root(
        rx.context_menu.trigger(
            platform_tile(
                platform_entry.platform.config.instance_name,
                platform_entry.platform.config.instance_name,
                on_click=NavigationState.route_to_platform(platform_entry.platform.config.instance_name)
            )
        ),
        # TODO: Implement the deletion functionality, perhaps a confirmation modal for running platforms and such.
        rx.context_menu.content(
            rx.context_menu.item(
                "Delete",
                color_scheme="red",
                # disabled=True
                # on_click
            )
        )
    )

def platform_overview() -> rx.Component:

    return rx.flex(
        rx.foreach(
            PlatformState.in_file_platforms,
            lambda platform: craft_new_platform_tile(platform)
        ),
        wrap="wrap",
        spacing="6",
        direction="row",
        padding="1rem"
    )