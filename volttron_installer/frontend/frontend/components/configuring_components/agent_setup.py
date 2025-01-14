import reflex as rx 
from ..form_components import *
# from .state import

def return_agent_name_field() -> rx.Component: 
    return form_entry.form_entry(
        "Agent Name",
        rx.text_field(
            # default_value=HostState.agent_path_value,
            # on_change=lambda : HostState.changing_state_values(HostState.agent_path_value)
        )
    )

def return_vip_identity_field() -> rx.Component: 
    return form_entry.form_entry(
        "Vip Identity",
        rx.text_field(
            # default_value="HostState.agent_path_value",
            # on_change=lambda : HostState.changing_state_values(HostState.agent_path_value)
        )
    )

def return_agent_path_field() -> rx.Component: 
    return form_entry.form_entry(
        "Identity File",
        rx.text_field(
            # default_value="HostState.agent_path_value",
            # on_change=lambda : HostState.changing_state_values(HostState.agent_path_value)
        )
    )

def return_agent_configuration_field() -> rx.Component: 
    return form_entry.form_entry(
        "Agent Configuration",
        rx.button("Add Configurations")
    )

def return_agent_entries() -> list[rx.Component]:
    return [
            return_agent_name_field(),
            return_vip_identity_field(),
            return_agent_path_field(),
            return_agent_configuration_field()
        ]

def agent_setup_instance() -> list[rx.Component]:
    return form_view.form_view_wrapper(
        return_agent_entries()
        )