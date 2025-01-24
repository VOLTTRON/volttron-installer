import reflex as rx 
from .. import form_components as fcomps
from .state import ConfigTemplatesTabState
from ..buttons.setup_button import setup_button
from ..configuring_components import config_templates 
import typing


def craft_form_from_data(component_id: str) -> rx.Component:
    return config_templates.config_templates_instance(component_id)


def craft_tile_from_data(entry: typing.List) -> rx.Component:
    component_id = entry[0]

    return fcomps.form_selection_button.form_selection_button(
        text=rx.cond(
            ConfigTemplatesTabState.committed_template_forms.contains(component_id),
            ConfigTemplatesTabState.committed_template_forms[component_id]["config_name"],
            ""
        ),
        selection_id=component_id,
        selected_item=ConfigTemplatesTabState.selected_id,
        on_click = ConfigTemplatesTabState.handle_selected_tile(component_id),
    )


def config_store_templates_tab() -> rx.Component:
    return fcomps.form_tab.form_tab(
        fcomps.form_tile_column.form_tile_column_wrapper(
            setup_button(
                "Create a Template",
                on_click = lambda : ConfigTemplatesTabState.generate_new_form_tile()
            ),
            rx.foreach(
                ConfigTemplatesTabState.config_template_forms,
                craft_tile_from_data
            )
        ),
        fcomps.form_view.form_view_wrapper(
            rx.cond(
                ConfigTemplatesTabState.selected_id != "",
                    rx.cond(
                        ConfigTemplatesTabState.config_template_forms.contains(ConfigTemplatesTabState.selected_id),
                        craft_form_from_data(ConfigTemplatesTabState.selected_id),
                        # rx.text(HostsTabState.selected_id),
                        rx.text("Invalid Template selected")
                    ),
                    rx.text("Select a Template to view or edit")
                )
            )
        )
    