import reflex as rx
from ...pages.platform_page import Instance

def platform_tile(platform_uid: str, platform_item: Instance, **props) -> rx.Component:
    return rx.flex(
        rx.hstack(
            rx.text(platform_uid),
            rx.text(""),
            justify="between"
        ),
        direction="column",
        class_name="platform_tile",
        **props
    )
