import reflex as rx
from . import platform_agent_config_store
from ..configuring_components import agent_config
from ..form_components import *
from .state import AgentSetupTabState
from ..buttons import setup_button


def agent_config_tab(platform_uid: str) -> rx.Component:

    return rx.vstack(
        #agent_config.agent_config_whatever(),
        rx.box(
            agent_config.agent_config_form(platform_uid)
        ),
        rx.box(
            platform_agent_config_store.agent_config_store_section(platform_uid)
        ),
        justify="start",
        spacing="6"
    )