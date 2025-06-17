import reflex as rx
from .app_layout import app_layout
from ..components.sidebar_components.app_sidebar import app_sidebar

def app_layout_sidebar(*children)-> rx.Component:
    return rx.hstack(
        app_sidebar(),
        *children,
        height="100vh",
        width="100%",
        overflow="hidden",
    )