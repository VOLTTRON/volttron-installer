# hosts.py
import reflex as rx
from ..form_components import *
from ..tabs import state


def host_form(component_id: str) -> rx.Component:
    
    return rx.form(
        form_view.form_view_wrapper(
            form_entry.form_entry(
                "Host Id",
                rx.input(
                    value=state.HostsTabState.host_forms[component_id]["host_id"],
                    on_change=lambda v: state.HostsTabState.update_form_field(component_id, "host_id", v),
                    required=True,
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "SSH Sudo User", 
                rx.input(
                    value=state.HostsTabState.host_forms[component_id]["ssh_sudo_user"],
                    on_change=lambda v: state.HostsTabState.update_form_field(component_id, "ssh_sudo_user", v),
                    required=True,
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Identity File",
                rx.input(
                    value=state.HostsTabState.host_forms[component_id]["identity_file"],
                    on_change=lambda v: state.HostsTabState.update_form_field(component_id, "identity_file", v),
                    required=True,
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "SSH IP Address",
                rx.input(
                    value=state.HostsTabState.host_forms[component_id]["ssh_ip_address"],
                    on_change=lambda v: state.HostsTabState.update_form_field(component_id, "ssh_ip_address", v),
                    required=True,
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "SSH Port",
                rx.input(
                    value=state.HostsTabState.host_forms[component_id]["ssh_port"],
                    on_change=lambda v: state.HostsTabState.update_form_field(component_id, "ssh_port", v),
                    required=True,
                ),
                required_entry=True
            ),
            rx.hstack(
                rx.button(
                    "Save",
                    type="submit"
                ),
                justify="end"
            ),
        ),
        on_submit=lambda: state.HostsTabState.save_form(component_id),
        reset_on_submit=False
    )
