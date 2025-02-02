import reflex as rx
from ..form_components import *
from ..tabs.state import ConfigTemplatesTabState
from ..custom_fields import text_editor, csv_field
from ..buttons.upload_button import upload_button

def config_templates_instance(component_id: str) -> list[rx.Component]:
    return form_view.form_view_wrapper(
        form_entry.form_entry(
            "Config Name",
            rx.text_field(
                value= ConfigTemplatesTabState.config_template_forms[component_id]["config_name"],
                on_change= lambda v: ConfigTemplatesTabState.update_form_field(component_id, "config_name", v)
            ),
            required_entry=True
        ),
        form_entry.form_entry(
            "Config Type",
            rx.radio(
                ["JSON", "CSV"],
                value=ConfigTemplatesTabState.config_template_forms[component_id]["config_type"],
                on_change= lambda v: ConfigTemplatesTabState.update_form_field(component_id, "config_type", v)
            ),
            required_entry=True
        ),
        form_entry.form_entry(
            "Config",
            rx.cond(
                ConfigTemplatesTabState.config_template_forms[component_id]["config_type"] == "CSV",
                csv_field.csv_data_field(),
                text_editor.text_editor(    
                    value=ConfigTemplatesTabState.config_template_forms[component_id]["config"],
                    on_change= lambda v: ConfigTemplatesTabState.update_form_field(component_id, "config", v)
                ),
            ),
            upload=rx.upload.root(
                upload_button(),
                accept=["json", "csv"]
            ),
            required_entry=True
        ),
        rx.hstack(
            rx.button(
                "Save",
                on_click= lambda : ConfigTemplatesTabState.save_form(component_id)
            ),
            justify="end"
        )
    )