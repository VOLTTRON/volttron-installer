import reflex as rx

from ..form_components import *
from ..buttons import setup_button, upload_button

def craft_config_store_view(platform_uid: str ) -> rx.Component:
    return rx.form(
        form_entry.form_entry(
            "Config Name",
            rx.text_field(
                # value= ConfigTemplatesTabState.config_template_forms[component_id]["config_name"],
                # on_change= lambda v: ConfigTemplatesTabState.update_form_field(component_id, "config_name", v)
            ),
            required_entry=True
        ),
        form_entry.form_entry(
            "Config Type",
            rx.radio(
                ["JSON", "CSV"],
                # value=ConfigTemplatesTabState.config_template_forms[component_id]["config_type"],
                # on_change= lambda v: ConfigTemplatesTabState.update_form_field(component_id, "config_type", v)
            ),
            required_entry=True
        ),
        form_entry.form_entry(
            "Config",
            rx.text_field(),
            # rx.cond(
                # ConfigTemplatesTabState.config_template_forms[component_id]["config_type"] == "CSV",
                # csv_field.csv_data_field(),
                # text_editor.text_editor(    
                    # value=ConfigTemplatesTabState.config_template_forms[component_id]["config"],
                    # on_change= lambda v: ConfigTemplatesTabState.update_form_field(component_id, "config", v)
                # ),
            # ),
            upload=rx.upload.root(
                upload_button.upload_button(),
                accept=["json", "csv"]
            ),
            required_entry=True
        ),
        rx.hstack(
            rx.button(
                "Save",
                type="submit"
                # on_click= lambda : ConfigTemplatesTabState.save_form(component_id)
            ),
            justify="end"
        ),
        # on_submit= lambda: submit bro
    )

def agent_config_store_section( platform_uid: str ) -> rx.Component:
    return form_tab.form_tab(
        form_tile_column.form_tile_column_wrapper(
            setup_button.setup_button(
                "Create a Config Entry",

            )
        ),
        form_view.form_view_wrapper(

        )
    )