import reflex as rx
from ..form_components import *
from ...state import HostState
        
def return_host_id_field() -> rx.Component: 
    return form_entry.form_entry(
        "Host Id",
        rx.text_field(
            # default_value=HostState.identity_file_value,
            # on_change=lambda : HostState.changing_state_values(HostState.identity_file_value)
        )
    )

def return_ssh_sudo_user_field() -> rx.Component: 
    return form_entry.form_entry(
        "SSH Sudo User",
        rx.text_field(
            # default_value="HostState.identity_file_value",
            # on_change=lambda : HostState.changing_state_values(HostState.identity_file_value)
        )
    )

def return_identity_file_field() -> rx.Component: 
    return form_entry.form_entry(
        "Identity File",
        rx.text_field(
            # default_value="HostState.identity_file_value",
            # on_change=lambda : HostState.changing_state_values(HostState.identity_file_value)
        )
    )

def return_ssh_ip_address_field() -> rx.Component: 
    return form_entry.form_entry(
        "SSH IP Address",
        rx.text_field(
            # default_value="HostState.identity_file_value",
            # on_change=lambda : HostState.changing_state_values(HostState.identity_file_value)
        )
    )

def return_ssh_port_field() -> rx.Component: 
    return form_entry.form_entry(
        "SSH Port",
        rx.text_field(
            # default_value="HostState.identity_file_value",
            # on_change=lambda : HostState.changing_state_values(HostState.identity_file_value)
        )
    )


def return_host_entries() -> list[rx.Component]:
    return [
            return_host_id_field(),
            return_ssh_sudo_user_field(),
            return_identity_file_field(),
            return_ssh_ip_address_field(),
            return_ssh_port_field()
        ]

def host_instance() -> list[rx.Component]:
    return form_view.form_view_wrapper(
        return_host_entries()
        )