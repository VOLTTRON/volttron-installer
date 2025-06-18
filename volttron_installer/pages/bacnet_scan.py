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
                    value=BacnetScanState.open_accordion_items,
                    on_value_change=BacnetScanState.set_open_items,
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
                rx.cond(BacnetScanState.proxy_up==False, rx.text("**A proxy must be up to use this tool.**", color_scheme="red")),
                spacing="6",
                align="start",
            ),
            padding="2rem",
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
                    form_entry.form_entry(
                        "Device Instance Low", 
                        rx.input(
                            value=BacnetScanState.request_who_is.device_instance_low,
                            on_change=lambda value: BacnetScanState.request_who_is_input("device_instance_low", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Device Instance High", 
                        rx.input(
                            value=BacnetScanState.request_who_is.device_instance_high,
                            on_change=lambda value: BacnetScanState.request_who_is_input("device_instance_high", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Dest", 
                        rx.input(
                            value=BacnetScanState.request_who_is.dest,
                            on_change=lambda value: BacnetScanState.request_who_is_input("dest", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    spacing="6",
                    align="start",
                    style={"color": "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Request Who Is",
                        variant="surface",
                        on_click=BacnetScanState.handle_request_who_is,
                        disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            ),
            on_submit=BacnetScanState.handle_request_who_is
        )

def read_device_all_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    form_entry.form_entry(
                        "Device Address", 
                        rx.input(
                            value=BacnetScanState.read_device_all.device_address,
                            on_change=lambda value: BacnetScanState.read_device_all_input("device_address", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Device Object Identifier", 
                        rx.input(
                            value=BacnetScanState.read_device_all.device_object_identifier,
                            on_change=lambda value: BacnetScanState.read_device_all_input("device_object_identifier", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    spacing="6",
                    align="start",
                    style={"color": "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Read Device All",
                        variant="surface",
                        on_click=BacnetScanState.handle_read_device_all,
                        disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            ),
            on_submit=BacnetScanState.handle_read_device_all
        )

def scan_ip_range_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    form_entry.form_entry(
                        "Network String", 
                        rx.input(
                            value=BacnetScanState.scan_ip_range.network_string,
                            on_change=lambda value: BacnetScanState.scan_ip_range_input("network_string", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    spacing="6",
                    align="start",
                    style={"color": "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Scan IP",
                        variant="surface",
                        on_click=BacnetScanState.handle_scan_ip_range,
                        disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            ),
            on_submit=BacnetScanState.handle_scan_ip_range
        )

def ping_ip_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    form_entry.form_entry(
                        "IP Address", 
                        rx.input(
                            value=BacnetScanState.ping_ip.ip_address,
                            on_change=lambda value: BacnetScanState.ping_ip_input("ip_address", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    spacing="6",
                    align="start",
                    style={"color": "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Ping IP",
                        variant="surface",
                        on_click=BacnetScanState.handle_ping_ip,
                        disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            ),
            on_submit=BacnetScanState.handle_ping_ip
        )

def read_property_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    form_entry.form_entry(
                        "Device Address", 
                        rx.input(
                            value=BacnetScanState.read_property.device_address,
                            on_change=lambda value: BacnetScanState.read_property_input("device_address", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Object Identifier", 
                        rx.input(
                            value=BacnetScanState.read_property.object_identifier,
                            on_change=lambda value: BacnetScanState.read_property_input("object_identifier", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Property Identifier", 
                        rx.input(
                            value=BacnetScanState.read_property.property_identifier,
                            on_change=lambda value: BacnetScanState.read_property_input("property_identifier", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Property Array Index", 
                        rx.input(
                            value=BacnetScanState.read_property.property_array_index,
                            on_change=lambda value: BacnetScanState.read_property_input("property_array_index", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        )
                    ),
                    spacing="6",
                    align="start",
                    style={"color": "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Read Property",
                        variant="surface",
                        on_click=BacnetScanState.handle_read_property,
                        disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            ),
            on_submit=BacnetScanState.handle_read_property
        )

def write_property_accordion_content() -> rx.Component:
    return rx.form(
            rx.vstack(
                rx.vstack(
                    form_entry.form_entry(
                        "Device Address", 
                        rx.input(
                            value=BacnetScanState.write_property.device_address,
                            on_change=lambda value: BacnetScanState.write_property_input("device_address", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Object Identifier", 
                        rx.input(
                            value=BacnetScanState.write_property.object_identifier,
                            on_change=lambda value: BacnetScanState.write_property_input("object_identifier", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Property Identifier", 
                        rx.input(
                            value=BacnetScanState.write_property.property_identifier,
                            on_change=lambda value: BacnetScanState.write_property_input("property_identifier", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Value", 
                        rx.input(
                            value=BacnetScanState.write_property.value,
                            on_change=lambda value: BacnetScanState.write_property_input("value", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Priority", 
                        rx.input(
                            value=BacnetScanState.write_property.priority,
                            on_change=lambda value: BacnetScanState.write_property_input("priority", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        ), 
                        required_entry=True
                    ),
                    form_entry.form_entry(
                        "Property Array Index", 
                        rx.input(
                            value=BacnetScanState.write_property.property_array_index,
                            on_change=lambda value: BacnetScanState.write_property_input("property_array_index", value),
                            disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                        )
                    ),
                    spacing="6",
                    align="start",
                    style={"color": "white"}
                ),
                rx.hstack(
                    rx.button(
                        "Write Property",
                        variant="surface",
                        on_click=BacnetScanState.handle_write_property,
                        disabled=rx.cond(BacnetScanState.proxy_up, False, True)
                    ),
                    align="end"
                ),
                spacing="6",
                align="center",
                padding="2rem",
            ),
            on_submit=BacnetScanState.handle_write_property
        )

@rx.page(route="/tools/bacnet_scan")
def bacnet_scan_page() -> rx.Component:
    return app_layout_sidebar.app_layout_sidebar(
        bacnet_scan(),
    )
