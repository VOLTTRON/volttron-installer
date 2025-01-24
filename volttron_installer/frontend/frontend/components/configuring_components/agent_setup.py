import reflex as rx
from ..form_components import *
from ..tabs.state import AgentSetupTabState, ConfigTemplatesTabState

def agent_setup_form(component_id: str) -> list[rx.Component]:
    return rx.form(  # Wrap in form for validation
        form_view.form_view_wrapper(
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
                "Vip Identity", 
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
                                                lambda x: rx.select.item(
                                                    x[1]["config_name"],
                                                    value=x[1]["config_name"]
                                                )
                                             )
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
                        on_submit=AgentSetupTabState.handle_config_submit,
                        reset_on_submit=True
                    )
                )
            )
        ),
            rx.hstack(
                rx.button(
                    "Save",
                    type="submit",  # Changed to submit type for form validation
                ),
                justify="end"
            )
        ),
        on_submit=lambda: AgentSetupTabState.save_form(component_id),
        prevent_default=True,
        reset_on_submit=False  # Don't reset form after submission
    )