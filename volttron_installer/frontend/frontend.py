import reflex as rx
from . import components
from .styles import styles
from . import state
from .pages import index, platform_page

app = rx.App(
    style=styles.styles
)
