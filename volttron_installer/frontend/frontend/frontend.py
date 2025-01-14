import reflex as rx
from . import components
from .styles import styles
from . import state
from .pages import index

app = rx.App(
    style=styles.styles
)

app.add_page(index)