import reflex as rx
from ..state import BacnetScanState
from ..components.form_components import form_entry
from ..layouts import app_layout_sidebar

def bacnet_scan() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.form(
                        form_entry.form_entry(
                        "IP Address",
                        rx.hstack(
                            rx.input(),
                            rx.button(
                                rx.cond(
                                    BacnetScanState.proxy_up,
                                    "Stop Proxy",
                                    "Start Proxy",
                                ),
                                loading=BacnetScanState.is_starting_proxy,
                                color_scheme=rx.cond(
                                    BacnetScanState.proxy_up,
                                    "red",
                                    "primary"
                                ),
                                on_click=BacnetScanState.toggle_proxy
                            )
                        ),
                    )
                ),
                rx.accordion.root(
                    rx.accordion.item(
                        header="Write Property",
                        content=write_property_accordion_content(),
                        value="1"
                    ),
                    rx.accordion.item(
                        header="Read Property",
                        content=read_property_accordion_content(),
                        value="2"
                    ),
                    rx.accordion.item(
                        header="Ping IP",
                        content=ping_ip_accordion_content(),
                        value="3"
                    ),
                    rx.accordion.item(
                        header="Scan IP Range",
                        content=scan_ip_range_accordion_content(),
                        value="4"
                    ),
                    rx.accordion.item(
                        header="Read Device All",
                        content=read_device_all_accordion_content(),
                        value="5"
                    ),
                    rx.accordion.item(
                        header="Request Who Is",
                        content=request_who_is_accordion_content(),
                        value="6",
                    ),
                    collapsible=True,
                    variant="outline",                    
                    width="100%",
                    type="multiple",
                    color_scheme=rx.cond(
                        BacnetScanState.proxy_up,
                        "blue",
                        "red"
                    ),
                    disabled=rx.cond(
                        BacnetScanState.proxy_up,
                        False,
                        True
                    ),
                ),
                spacing="6",
                align="start",
            ),
            padding_top="2rem",
            align="center",
            justify="center",
            width="100%",
        ),
        overflow_y="auto",
        height="100%",
        width="100%",
    )

def request_who_is_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    # TODO implement on_change functionality for these inputs, have them save their
                    # values for everything
                    form_entry.form_entry("Device Instance Low", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Device Instance High", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Dest", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    spacing="6",
                    align="start",
                    style={"color" : "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Request Who Is",
                        # disabled = write_property_not_ready
                        # color_scheme="primary",
                        # on_click=BacnetScanState.write_property
                        variant="surface",
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
        )
    )

def read_device_all_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    # TODO implement on_change functionality for these inputs, have them save their
                    # values for everything
                    form_entry.form_entry("Device Address", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Device Object Identifier", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    spacing="6",
                    align="start",
                    style={"color" : "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Read Device All",
                        # disabled = write_property_not_ready
                        # color_scheme="primary",
                        # on_click=BacnetScanState.write_property
                        variant="surface",
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            )
        )

def scan_ip_range_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    # TODO implement on_change functionality for these inputs, have them save their
                    # values for everything
                    form_entry.form_entry("Network String", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    spacing="6",
                    align="start",
                    style={"color" : "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Scan IP",
                        # disabled = write_property_not_ready
                        # color_scheme="primary",
                        # on_click=BacnetScanState.write_property
                        variant="surface",
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            )
        )

def ping_ip_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    # TODO implement on_change functionality for these inputs, have them save their
                    # values for everything
                    form_entry.form_entry("IP Address", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    spacing="6",
                    align="start",
                    style={"color" : "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Ping IP",
                        # disabled = write_property_not_ready
                        # color_scheme="primary",
                        # on_click=BacnetScanState.write_property
                        variant="surface",
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            )
        )

def read_property_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    # TODO implement on_change functionality for these inputs, have them save their
                    # values for everything
                    form_entry.form_entry("Device Address", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Object Identifier", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Property Identifier", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Property Array Index", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True))), # int, optional
                    spacing="6",
                    align="start",
                    style={"color" : "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Read Property",
                        # disabled = write_property_not_ready
                        # color_scheme="primary",
                        # on_click=BacnetScanState.write_property
                        variant="surface",
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            )
        )

def write_property_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    # TODO implement on_change functionality for these inputs, have them save their
                    # values for everything
                    form_entry.form_entry("Device Address", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Object Identifier", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Property Identifier", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Value", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # str
                    form_entry.form_entry("Priority", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True)), required_entry=True), # int
                    form_entry.form_entry("Property Array Index", rx.input(disabled=rx.cond(BacnetScanState.proxy_up,False,True))), # int, optional
                    spacing="6",
                    align="start",
                    style={"color" : "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Write Property",
                        # disabled = write_property_not_ready
                        # color_scheme="primary",
                        # on_click=BacnetScanState.write_property
                        variant="surface",
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            )
        )

@rx.page(route="/tools/bacnet_scan")
def bacnet_scan_page() -> rx.Component:
    return app_layout_sidebar.app_layout_sidebar(
        bacnet_scan(),
    )
