import typing
import reflex as rx
from ..form_components import *
from ..tabs.state import AgentSetupTabState, ConfigTemplatesTabState
from ..buttons.setup_button import setup_button
from ..buttons.delete_icon_button import delete_icon_button

# TODO
# - need to complete the agent config store view
def craft_config_entry_tile(config_entry: typing.Tuple) -> rx.Component:
    # config_name = config_entry[0]
    return rx.box()
    # return form_selection_button.form_selection_button(
    #     text="config_entry",
    #     selection_id="config_entry",
    #     selected_item=AgentSetupTabState.selected_config_store_entry,
    #     # on_click=AgentSetupTabState.change_selected_config_entry(config_entry),
    #     delete_component=delete_icon_button()
    # )


def agent_config_templates_view(agent_component_id: str) -> rx.Component:
    return form_tab.form_tab(
        form_tile_column.form_tile_column_wrapper(
            # rx.foreach(
            #     AgentSetupTabState.agent_forms[agent_component_id]["agent_config_store"],
            #     craft_config_entry_tile
            # )
            rx.box()
        ),
        rx.box()
    )

def agent_setup_form(component_id: str) -> rx.Component:
    return form_view.form_view_wrapper(
            form_entry.form_entry(
                "Agent Name",
                rx.input(  # Changed to rx.input for form validation
                    value=AgentSetupTabState.agent_forms[component_id]["agent_name"],
                    on_change=lambda v: AgentSetupTabState.update_form_field(component_id, "agent_name", v),
                    required=True,
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Identity", 
                rx.input(
                    value=AgentSetupTabState.agent_forms[component_id]["vip_identity"],
                    on_change=lambda v: AgentSetupTabState.update_form_field(component_id, "vip_identity", v),
                    required=True,
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Identity File",
                rx.input(
                    value=AgentSetupTabState.agent_forms[component_id]["identity_file"],
                    on_change=lambda v: AgentSetupTabState.update_form_field(component_id, "identity_file", v),
                    required=True,
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Config Store Entries",
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.button(
                            "Add",
                            variant="soft"
                        )
                    ),
                    rx.dialog.content(
                        rx.dialog.title("Add Configuration"),
                        rx.form(
                            rx.flex(
                                form_entry.form_entry(
                                    "Config Store Templates",
                                    rx.select.root(
                                        rx.select.trigger(),
                                        rx.select.content(
                                            rx.select.group(
                                                rx.foreach(
                                                    ConfigTemplatesTabState.committed_template_forms,
                                                    # ( component_id, dict["name" : xxx] )
                                                    lambda x: rx.select.item(
                                                        x[1]["config_name"],
                                                        value=x[1]["config_name"]
                                                    )
                                                ),
                                            )
                                        ),
                                        name="template"
                                    )
                                ),
                                form_entry.form_entry(
                                    "Config Name",
                                    rx.input(
                                        name="config_name",
                                        required=True,
                                        placeholder="Enter config name"
                                    ),
                                    required_entry=True,
                                ),
                                rx.flex(
                                    rx.dialog.close(
                                        rx.button(
                                            "Cancel",
                                            variant="soft",
                                            color_scheme="tomato"
                                        )
                                    ),
                                    rx.dialog.close(
                                        rx.button(
                                            "Save",
                                            type="submit",
                                            on_click=rx.stop_propagation
                                        )
                                    ),
                                    justify="between",
                                    direction="row"
                                ),
                                spacing="6",
                                direction="column"
                            ),
                            on_submit=lambda form_data: AgentSetupTabState.handle_config_submit(form_data, component_id),
                            reset_on_submit=True
                        )
                    )
                )
            ),
            # Config Store templates view
            agent_config_templates_view(component_id),
            rx.hstack(
                rx.button(
                    "Save",
                    on_click=lambda: AgentSetupTabState.save_form(component_id),  # Changed to submit type for form validation
                ),
                justify="end"
            )
        )