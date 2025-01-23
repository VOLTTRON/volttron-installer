import reflex as rx
from ..form_components import *
from ..tabs.state import AgentSetupTabState

def agent_setup_form(component_id: str) -> list[rx.Component]:
    return form_view.form_view_wrapper(
        form_entry.form_entry(
            "Agent Name",
            rx.text_field(
                value= AgentSetupTabState.agent_forms[component_id]["agent_name"],
                on_change= lambda v: AgentSetupTabState.update_form_field(component_id, "agent_name", v)
            )
        ),
        form_entry.form_entry(
            "Vip Identity",
            rx.text_field(
                value=AgentSetupTabState.agent_forms[component_id]["vip_identity"],
                on_change= lambda v: AgentSetupTabState.update_form_field(component_id, "vip_identity", v)
            )
        ),
        form_entry.form_entry(
            "Identity File",
            rx.text_field(    
                value=AgentSetupTabState.agent_forms[component_id]["vip_identity"],
                on_change= lambda v: AgentSetupTabState.update_form_field(component_id, "vip_identity", v)
            )
        ),
        form_entry.form_entry(
            "Config Store Entries",
            rx.button("Add")
        ),
        rx.hstack(
            rx.button(
                "Save"
            ),
            justify="end"
        )
    )