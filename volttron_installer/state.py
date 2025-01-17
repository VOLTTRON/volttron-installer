import reflex as rx
from pathlib import Path
from .settings import get_settings


class State(rx.State):
    """The app state."""

    ...


settings = get_settings()

class SettingsState(rx.State):
    """The settings state."""

    app_name: str = settings.app_name
    secret_key: str = settings.secret_key

    _upload_dir: str = settings.upload_dir
    _data_dir: str = settings.data_dir



