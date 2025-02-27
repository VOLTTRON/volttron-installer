import reflex as rx

from .. import form_components as fcomps
from .state import ConfigTemplatesTabState
from ..buttons.delete_icon_button import delete_icon_button
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
        delete_component=delete_icon_button()
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
    



# import reflex as rx 
# from .. import form_components as fcomps
# from .state import ConfigTemplatesTab
# from ..buttons.delete_icon_button import delete_icon_button
# from ..buttons.setup_button import setup_button
# from ..configuring_components import config_templates 
# from ...modules.state import ConfigTemplates
# import typing


# def craft_form_from_data(selected_form_uid: str) -> rx.Component:
    
#     form_uid = selected_form_uid
#     config_name = ConfigTemplatesTab.config_form_uids[selected_form_uid]

#     return config_templates.config_templates_instance(form_uid, config_name)


# def craft_tile_from_data(entry: typing.List) -> rx.Component:
#     print("we are running? at all?")
#     config_name = entry[0]
#     uid = generate_new_component_id("config_template")

#     return fcomps.form_selection_button.form_selection_button(
#         text=config_name,
#         selection_id=uid,
#         selected_item=ConfigTemplatesTab.selected_id,
#         on_click = ConfigTemplatesTab.handle_selected_id(uid),
#         delete_component=delete_icon_button()
#     )


# def config_store_templates_tab() -> rx.Component:
#     return fcomps.form_tab.form_tab(
#         fcomps.form_tile_column.form_tile_column_wrapper(
#             setup_button(
#                 "Create a Template",
#                 on_click = lambda : ConfigTemplatesTab.create_blank_form()
#             ),
#             rx.foreach(
#                 ConfigTemplatesTab.config_form_uids,
#                 craft_tile_from_data,
#             )
#         ),
#         fcomps.form_view.form_view_wrapper(
#             rx.cond(
#                 ConfigTemplatesTab.selected_id != "",
#                     rx.cond(
#                         ConfigTemplatesTab.config_form_uids.contains(ConfigTemplatesTab.selected_id),
#                         craft_form_from_data(ConfigTemplatesTab.selected_id),
#                         # rx.text(HostsTabState.selected_id),
#                         rx.text("Invalid Template selected")
#                     ),
#                     rx.text("Select a Template to view or edit")
#                 )
#             )
#         )


# def generate_new_component_id(type: str = "___"):
#     import random
#     return f"{type}-component-{random.randint(0, 300)}"
