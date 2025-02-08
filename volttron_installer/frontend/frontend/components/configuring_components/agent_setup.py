import reflex as rx
from ..form_components import *
from ..tabs.state import AgentSetupTabState, ConfigTemplatesTabState
from ..buttons.setup_button import setup_button

def agent_config_templates_view(component_id: str) -> list[rx.Component]:
    return form_tab.form_tab(
        form_tile_column.form_tile_column_wrapper(

        )
    )

def agent_setup_form(component_id: str) -> list[rx.Component]:
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
            rx.box(

            ),
            rx.hstack(
                rx.button(
                    "Save",
                    on_click=lambda: AgentSetupTabState.save_form(component_id),  # Changed to submit type for form validation
                ),
                justify="end"
            )
        )