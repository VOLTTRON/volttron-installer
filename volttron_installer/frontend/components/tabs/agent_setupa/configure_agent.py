import reflex as rx
from ...form_components import *
from ...custom_fields import text_editor
from ..tab_states import AgentTabContent, AgentSetupTab



def agent_setup_form(agent_tab_content: AgentTabContent) -> rx.Component:
    return rx.form(
        form_view.form_view_wrapper(
            form_entry.form_entry(
                "Agent Name",
                rx.input(
                    value=agent_tab_content.agent_entry.agent_name,
                    on_change=lambda value: AgentSetupTab.update_agent_detail(agent_tab_content.tab_content_id, "agent_name", value),
                    required=True,
                    name="agent_name"
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Identity", 
                rx.input(
                    value=agent_tab_content.agent_entry.identity,
                    on_change=lambda value: AgentSetupTab.update_agent_detail(agent_tab_content.tab_content_id, "identity", value),
                    required=True,
                    name="identity"
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Agent Path",
                rx.input(
                    value=agent_tab_content.agent_entry.agent_path,
                    on_change=lambda value: AgentSetupTab.update_agent_detail(agent_tab_content, "agent_path", value),
                    required=True,
                    name="agent_path"
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Agent Config",
                text_editor.text_editor(
                    value=agent_tab_content.agent_entry.agent_config,
                    on_change=lambda value: AgentSetupTab.update_agent_detail(agent_tab_content.tab_content_id, "agent_config", value),
                    required=True,
                    name="agent_config"
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
                                    rx.select(
                                        ["thing1"],
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
                            # on_submit=lambda form_data: AgentSetupTabState.handle_config_submit(form_data, component_id),
                            reset_on_submit=True
                        )
                    )
                )
            ),
            rx.hstack(
                rx.button(
                    "Save",
                    type="submit",
                    on_click=lambda: AgentSetupTab.commit_agent(agent_tab_content.tab_content_id)
                ),
                justify="end"
            ),
        ),
        # on_submit=lambda: HostTab.commit_host(host_tab_content.tab_content_id),
        reset_on_submit=False
    )
