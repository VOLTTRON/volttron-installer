import reflex as rx

from ..backend.models import CreateInventoryRequest
from ..backend.endpoints import add_to_inventory


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

                # rx.hstack(
                #     rx.checkbox("Checked", name="check"),
                #     rx.switch("Switched", name="switch"),
                # ),
                rx.button("Submit", type="submit"),
            ),
            on_submit=FormState.handle_submit,
            reset_on_submit=True,
        ),
        rx.divider(),
        rx.heading("Results"),
        rx.text(str(FormState)),
    )
