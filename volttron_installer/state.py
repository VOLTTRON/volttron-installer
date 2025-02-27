import reflex as rx
from pathlib import Path
from .settings import get_settings
from . import backend as bk

class AppState(rx.State):
    """The app state."""
    # platforms
    # hosts
    # agents
    # templates
    # ==============
    # perhaps all of the fields above are filled out by the respective
    # backend methods, like list_of_x(). this will still be compatible
    # with our tab_states.py because we each of those states will 
    # inherit from this state. My thought process here is that I will
    # have to create tab_contents for each of x fields, then those will
    # be the forward facing models that will be used in the frontend. 

    ...


settings = get_settings()

class SettingsState(rx.State):
    """The settings state."""

    app_name: str = settings.app_name
    secret_key: str = settings.secret_key

    _upload_dir: str = settings.upload_dir
    _data_dir: str = settings.data_dir



