import reflex as rx

from ...backend.models import CreateInventoryRequest, Inventory, HostEntry
from ...backend.endpoints import add_to_inventory, get_inventory


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


    @rx.event
    def handle_submit(self, form_data: dict):
        request = CreateInventoryRequest(**form_data)
        add_to_inventory(request)
        yield InventoryState.update_inventory()

class InventoryState(rx.State):
    inventory: Inventory = Inventory()  # Initialize with empty inventory

    @rx.var
    def table_data(self) -> list[HostEntry]:
        """Safe access to hosts data"""
        try:
            print(self.inventory.host_entries)
            print(list(self.inventory.host_entries.values()))
            return list(self.inventory.host_entries.values()) if self.inventory else []
        except:
            return []

    @rx.event
    def update_inventory(self):
        self.inventory = get_inventory()


@rx.page(route="/add_inventory")
def add_inventory() -> rx.Component:
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
        rx.heading("Inventory"),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.cell("ID"),
                    rx.table.cell("User"),
                    rx.table.cell("Host"),
                )
            ),
            rx.table.body(
                rx.foreach(
                    InventoryState.table_data,
                    lambda host: rx.table.row(
                        rx.table.cell(host.id),
                        rx.table.cell(host.ansible_user),
                        rx.table.cell(host.ansible_host),
                        key=host.id
                    )
                )
            )
        ),
        rx.divider()
    )
