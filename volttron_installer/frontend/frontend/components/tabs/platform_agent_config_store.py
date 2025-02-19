import reflex as rx

from ..form_components import *
from ..buttons import setup_button, upload_button, delete_icon_button
from .state import PlatformOverviewState, PlatformState
from ..custom_fields import csv_field, text_editor

# TODO:
# Finish this

def craft_config_store_view( platform_uid: str ) -> rx.Component:
    return form_view.form_view_wrapper(
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
            text_editor.text_editor(),
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
    )

def agent_config_store_section( platform_uid: str ) -> rx.Component:
    return rx.cond(
        #                                    flip this operand to view
        PlatformOverviewState.selected_agent_component_id != "",
        form_tab.form_tab(
            form_tile_column.form_tile_column_wrapper(
                setup_button.setup_button(
                    "Create a Config Entry",

                ),
                # rx.foreach(
                #     PlatformOverviewState.platforms[platform_uid]["agents"],
                #     agent_config_template_tile
                # )
            ),
            form_view.form_view_wrapper(
                craft_config_store_view(platform_uid)
            )
        ),
        rx.text("Please select an agent to view its config store")
    )

def agent_config_template_tile(data: tuple[str, str])-> rx.Component:
    component_id = data [0]
    
    return form_selection_button.form_selection_button(
        # text=PlatformState.platform_data[component_id]["config_name"],
        text="",
        selection_item=PlatformOverviewState.selected_agent_config_template_id,
        selection_id=component_id,
        delete_component=delete_icon_button.delete_icon_button()
    )