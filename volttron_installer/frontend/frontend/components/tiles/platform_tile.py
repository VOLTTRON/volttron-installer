import reflex as rx
from ..tabs.state import PlatformOverviewState
from ...navigation.state import NavigationState

def platform_tile(**props) -> rx.Component:
    return rx.flex(
        rx.hstack(
            rx.text("bro"),
            rx.text("OFF"),
            justify="between"
        ),
        direction="column",
        class_name="platform_tile",
        **props
    )
