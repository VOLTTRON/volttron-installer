import reflex as rx
from ..form_components import *
from ..configuring_components import platform_configuration


def platform_config_tab( platform_uid: str ) -> rx.Component:
    return rx.container(
        platform_configuration.platform_config_form(platform_uid),
        padding="1rem"
    )