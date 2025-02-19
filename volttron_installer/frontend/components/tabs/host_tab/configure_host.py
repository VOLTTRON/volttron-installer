import reflex as rx
from ...form_components import *
from ..tab_states import HostTabContent, HostTab



def host_form(host_tab_content: HostTabContent) -> rx.Component:
    return rx.form(
        form_view.form_view_wrapper(
            form_entry.form_entry(
                "Host Id",
                rx.input(
                    value=host_tab_content.host_entry.host_id,
                    on_change=lambda value: HostTab.update_host_detail(host_tab_content.tab_content_id, "host_id", value),
                    required=True,
                    name="host_id"
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "SSH Sudo User", 
                rx.input(
                    value=host_tab_content.host_entry.ssh_sudo_user,
                    on_change=lambda value: HostTab.update_host_detail(host_tab_content.tab_content_id, "ssh_sudo_user", value),
                    required=True,
                    name="ssh_sudo_user"
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "Identity File",
                rx.input(
                    value=host_tab_content.host_entry.identity_file,
                    on_change=lambda value: HostTab.update_host_detail(host_tab_content.tab_content_id, "identity_file", value),
                    required=True,
                    name="identity_file"
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "SSH IP Address",
                rx.input(
                    value=host_tab_content.host_entry.ssh_ip_address,
                    on_change=lambda value: HostTab.update_host_detail(host_tab_content.tab_content_id, "ssh_ip_address", value),
                    required=True,
                    name="ssh_ip_address"
                ),
                required_entry=True
            ),
            form_entry.form_entry(
                "SSH Port",
                rx.input(
                    value=host_tab_content.host_entry.ssh_port,
                    on_change=lambda value: HostTab.update_host_detail(host_tab_content.tab_content_id, "ssh_port", value),
                    required=True,
                    name="ssh_port"
                ),
                required_entry=True
            ),
            rx.hstack(
                rx.button(
                    "Save",
                    type="submit",
                    on_click=lambda: HostTab.commit_host(host_tab_content.tab_content_id)
                ),
                justify="end"
            ),
        ),
        # on_submit=lambda: HostTab.commit_host(host_tab_content.tab_content_id),
        reset_on_submit=False
    )
