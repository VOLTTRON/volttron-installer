import reflex as rx
from ..form_components import *
from ..tabs.state import ConfigTemplatesTabState

def config_templates_instance(component_id: str) -> list[rx.Component]:
    return form_view.form_view_wrapper(
        form_entry.form_entry(
            "Config Name",
            rx.text_field(
                value= ConfigTemplatesTabState.config_template_forms[component_id]["config_name"],
                on_change= lambda v: ConfigTemplatesTabState.update_form_field(component_id, "config_name", v)
            )
        ),
        form_entry.form_entry(
            "Config Type",
            rx.radio(
                ["JSON", "YAML"],
                value=ConfigTemplatesTabState.config_template_forms[component_id]["config_type"],
                on_change= lambda v: ConfigTemplatesTabState.update_form_field(component_id, "config_type", v)
            )
        ),
        form_entry.form_entry(
            "Config",
            rx.text_field(    
                value=ConfigTemplatesTabState.config_template_forms[component_id]["config"],
                on_change= lambda v: ConfigTemplatesTabState.update_form_field(component_id, "config", v)
            )
        )
    )