import reflex as rx

from ..backend.models import CreateOrUpdateHostEntry, HostEntry
from ..backend.endpoints import add_host, get_hosts


class FormState(rx.State):

    entered_id: str = ""
    entered_user: str = ""
    entered_host: str = "localhost"
    entered_port: int = 22
    entered_http_proxy: str = ""
    entered_https_proxy: str = ""
    volttron_venv: str = ""
    host_configs_dir: str = ""

    # These are submitted values.
    id: str
    ansible_user: str
    ansible_host: str
    #ansible_connection: str = "local"
    # http_proxy: str | None = None
    # https_proxy: str | None = None
    # volttron_venv: str | None = None
    # host_configs_dir: str | None = None
    #request: CreateInventoryRequest




@rx.page(route="/add_host")
def add_host() -> rx.Component:
    return rx.vstack(
        rx.form(
            rx.vstack(
                rx.input(placeholder="id",
                         name="id",
                         on_change=FormState.set_entered_id),
                rx.input(placeholder="User",
                         name="ansible_user",
                         on_change=FormState.set_entered_user),
                rx.input(placeholder="Resolvable Host / IP",
                         name="ansible_host",
                         on_change=FormState.set_entered_host,
                         value=f"{FormState.entered_host}"),
                rx.button("Submit", type="submit"),
            ),
            on_submit=FormState.handle_submit,
            reset_on_submit=True,
        ),
        rx.divider(),
        rx.heading("Hosts"),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.cell("ID"),
                    rx.table.cell("User"),
                    rx.table.cell("Host"),
                )
            ),
            # rx.table.body(
            #     rx.foreach(
            #         HostsState.table_data,
            #         lambda host: rx.table.row(
            #             rx.table.cell(host.id),
            #             rx.table.cell(host.ansible_user),
            #             rx.table.cell(host.ansible_host),
            #             key=host.id
            #         )
            #     )
            # )
        ),
        rx.divider()
    )
