import typing
import reflex as rx 
from .state import PlatformOverviewState 
from ...pages.platform_page import State as PlatformState
from ..tiles.platform_tile import platform_tile
from ...navigation.state import NavigationState

def craft_new_platform_tile(platform_entry: tuple[str, typing.Any]) -> rx.Component:
    platform_uid = platform_entry[0]
    platform_item = platform_entry[1]
    return platform_tile(
        platform_uid,
        platform_item,
        on_click=NavigationState.route_to_platform(platform_uid)
    )

def platform_overview() -> rx.Component:

    return rx.flex(
        rx.foreach(
            PlatformState.platforms,
            craft_new_platform_tile
        ),
        wrap="wrap",
        spacing="6",
        direction="row",
        padding="1rem"
    )