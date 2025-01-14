import reflex as rx
from ..form_components import *


def return_config_name_field() -> rx.Component:
    return form_entry.form_entry(
        "Config Name",
        rx.text_field(

        )
    )

def return_config_type_field() -> rx.Component:
    return form_entry.form_entry(
        "Config Type",
        rx.radio(
            ["JSON", "YAML"],
            default_value="JSON",
            # direction="row",
        )
    )


def return_config_entries() -> list[rx.Component]:
    return [
            return_config_name_field(),
            return_config_type_field()
        ]


def config_templates_instance () -> list[rx.Component]:
    return form_view.form_view_wrapper(
        return_config_entries()
    )