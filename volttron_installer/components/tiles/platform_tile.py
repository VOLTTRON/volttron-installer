import reflex as rx
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...pages.platform_page import Instance

def platform_tile(
        platform_uid: str, 
        platform_item: "Instance", 
        background_color="rgba(145, 145, 145, 0.29)",
        **props
    ) -> rx.Component:
    return rx.flex(
        rx.grid(
            rx.text(platform_uid, size="2", grid_column="span 2"),
            # rx.text("Running", size="2"),
            # rx.text("Off", size="2"),
            spacing="2",
            columns="2"
        ),
        direction="column",
        background_color=background_color,
        cursor="pointer",
        width="9rem",
        height="9rem",
        padding=".25rem .75rem",
        border_radius=".5rem",
        user_select="none",
        **props
    )
