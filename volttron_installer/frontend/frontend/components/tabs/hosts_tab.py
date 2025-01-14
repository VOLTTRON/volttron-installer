import reflex as rx

from .. import form_components

class HostsTabState(rx.State):
    working_form: rx.Component
    # host_id_value: str = ""
    # ssh_sudo_user_value: str = ""
    # identity_file_value: str = ""
    # ssh_ip_address_value: str = ""
    # ssh_port_value: str = ""
    ...

def hosts_tab() -> rx.Component:
    # ok so firstly i need a left and right side,
    # then i need to populate each side with desired controls
    # starting with the left, we'll pass in a simple button
    # moving to the right, lets pass in all of the host fields
    # that we need, maybe create an on change function

    return rx.container(
        form_components.form_tile_column.form_tile_column_wrapper(
            rx.container(
                rx.button("dude")
            )
        ),
        form_components.form_view.form_view_wrapper(
            [
                form_components.form_entry.form_entry(
                    "entry",
                    rx.text_field
                )
            ]
        )
    )