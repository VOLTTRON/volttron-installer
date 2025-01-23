# hosts.py
import reflex as rx
from ..form_components import *
from ..tabs import state


def host_form(component_id: str) -> rx.Component:
    
    return form_view.form_view_wrapper(
        form_entry.form_entry(
            "Host Id",
            rx.text_field(
                value=state.HostsTabState.host_forms[component_id]["host_id"],
                on_change=lambda v: state.HostsTabState.update_form_field(component_id, "host_id", v)
            )
        ),
        form_entry.form_entry(
            "SSH Sudo User", 
            rx.text_field(
                value=state.HostsTabState.host_forms[component_id]["ssh_sudo_user"],
                on_change=lambda v: state.HostsTabState.update_form_field(component_id, "ssh_sudo_user", v)
            )
        ),
        form_entry.form_entry(
            "Identity File",
            rx.text_field(
                value=state.HostsTabState.host_forms[component_id]["identity_file"],
                on_change=lambda v: state.HostsTabState.update_form_field(component_id, "identity_file", v)
            )
        ),
        form_entry.form_entry(
            "SSH IP Address",
            rx.text_field(
                value=state.HostsTabState.host_forms[component_id]["ssh_ip_address"],
                on_change=lambda v: state.HostsTabState.update_form_field(component_id, "ssh_ip_address", v)
            )
        ),
        form_entry.form_entry(
            "SSH Port",
            rx.text_field(
                value=state.HostsTabState.host_forms[component_id]["ssh_port"],
                on_change=lambda v: state.HostsTabState.update_form_field(component_id, "ssh_port", v)
            )
        ),
        rx.hstack(
            rx.button(
                "Save"
            ),
            justify="end"
        )
    )
