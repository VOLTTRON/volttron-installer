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
                bacnet_proxy_card(),
                network_information_card(),
                scan_for_devices_card(),
                card_with_fake_devices(),
                card_with_no_devices(),
                property_operations_card(),
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

def scan_for_devices_card():
    return rx.box(
        rx.box(  # CardHeader
            rx.hstack(
                rx.icon("search", size=20),  # Substitute with the correct icon name if available
                rx.text("Step 3: Scan for Devices", size="5", weight="bold"),
                spacing="2",
                align="center"
            ),
            rx.text("Discover BACnet devices on your network", size="2", color="gray"),
            margin_bottom="0.8rem"
        ),
        rx.box(  # CardContent
            rx.vstack(
                rx.text("Network Range (CIDR)", as_="label", html_for="local-ip"),
                rx.input(
                    id="network_str",
                    placeholder="e.g. 192.168.1.0/24",
                    width="100%",
                    # value=ProxyState.local_ip,
                    # on_change=ProxyState.set_local_ip,
                ),
                rx.text(
                    "Leave blank to automatically select your machine's main outbound IP",
                    size="1",
                    color="gray",
                ),
                spacing="2",
                align="start",
            ),
            margin_bottom="0.8rem"
        ),
        rx.hstack(  # CardFooter
            rx.button(
                rx.icon("search", size=16),
                rx.text("Scan for Devices"),
                # on_click=ProxyState.start_proxy,
                # disabled=ProxyState.proxy_status == "running",
                variant="solid",
                justify="center",
                width="100%"
            ),
            justify="between",
            width="100%"
        ),
        border="1px solid",
        border_color="grey",
        border_radius=".5rem",
        box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        padding="1.3rem",
        # bg="white",
        max_width="400px"
    )



class MockTable(rx.State):
    fake_devices: list[dict [str,str]]= [
        {"name": "Device Alpha", "id": "1234", "address": "192.168.1.10"},
        {"name": "Device Beta", "id": "5678", "address": "192.168.1.12"},
        {"name": "Device Gamma", "id": "9012", "address": "192.168.1.14"},
    ]

def card_with_no_devices():
    return rx.box(
        rx.box(
            rx.text("Discovered Devices", size="5", weight="bold"),
            rx.text("No devices discovered yet", color="gray"),
            margin_bottom="1em",
        ),
        rx.box(
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Device Name"),
                            rx.table.column_header_cell("Object ID"),
                            rx.table.column_header_cell("IP Address"),
                        )
                    ),
                    rx.table.body(
                        rx.table.row(
                            rx.table.cell(
                                rx.text("No devices found. Run a scan to discover BACnet devices.", text_align="center", color="gray"),
                                col_span=3,
                            )
                        )
                    )
                ),
                height="300px",
                overflow_y="auto",
            ),
        ),
        border="1px solid",
        border_color="grey",
        border_radius=".5rem",
        box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        padding="1.3rem",
    )

def show_device(device: dict[str, str]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(device["name"]),
        rx.table.cell(device["id"]),
        rx.table.cell(device["address"]),
        class_name="csv_data_cell"
    )

def card_with_fake_devices() -> rx.Component:
    return rx.box(
        rx.box(
            rx.text("Discovered Devices", size="5", weight="bold"),
            rx.text(f"{MockTable.fake_devices.length()} BACnet devices found", color="gray"),
            margin_bottom="1em",
        ),
        rx.box(
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Device Name"),
                            rx.table.column_header_cell("Object ID"),
                            rx.table.column_header_cell("IP Address"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            MockTable.fake_devices,
                            show_device
                        )
                    )
                ),
                height="300px",
                overflow_y="auto",
            ),
        ),
        border="1px solid",
        border_color="grey",
        border_radius=".5rem",
        box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        padding="1.3rem",
    )





def property_operations_card():
    return rx.box(
        rx.box(  # Header
            rx.text("Property Operations", size="5", weight="bold"),
            rx.text("Read or write properties on selected device", size="2", color="gray"),
            margin_bottom="1rem"
        ),
        rx.tabs(
            rx.tabs.list(
                rx.tabs.trigger("Read Property", value="read"),
                rx.tabs.trigger("Write Property", value="write"),
                spacing="2",
                width="100%",
                margin_bottom="1rem"
            ),
            rx.tabs.content(
                # Read Tab
                rx.vstack(
                    form_entry.form_entry(
                        "Device Address",
                        rx.input(
                            id="read_device_address",
                            placeholder="e.g., 192.168.1.50",
                            read_only=True,
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Object Identifier",
                        rx.input(
                            id="read_object_identifier",
                            placeholder="e.g., device,506892",
                            read_only=True,
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Property Identifier",
                        rx.input(
                            id="read_property_identifier",
                            placeholder="e.g., description",
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Property Array Index (Optional)",
                        rx.input(
                            id="read_property_array_index",
                            placeholder="eg., 1",
                            width="100%",
                            type="number"
                        ),
                    ),
                    rx.button(
                        "Read Property",
                        width="100%",
                        # disabled, on_click omitted
                    ),
                    spacing="3"
                ),
                value="read"
            ),
            rx.tabs.content(
                # Write Tab
                rx.vstack(
                    form_entry.form_entry(
                        "Device Address",
                        rx.input(
                            id="write_device_address",
                            placeholder="e.g., 192.168.1.50",
                            read_only=True,
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Object Identifier",
                        rx.input(
                            id="write_object_identifier",
                            placeholder="e.g., device,506892",
                            read_only=True,
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Property Identifier",
                        rx.input(
                            id="write_property_identifier",
                            placeholder="e.g., description",
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Value",
                        rx.input(
                            id="write_value",
                            placeholder="e.g., some value",
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Priority",
                        rx.input(
                            id="write_priority",
                            placeholder="eg., 1",
                            width="100%",
                            type="number"
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Property Array Index (Optional)",
                        rx.input(
                            id="write_property_array_index",
                            placeholder="eg., 1",
                            width="100%",
                            type="number"
                        ),
                    ),
                    rx.button(
                        "Write Property",
                        width="100%",
                        # disabled, on_click omitted
                    ),
                    spacing="3"
                ),
                value="write"
            ),
            default_value="read",
            width="100%"
        ),
        border="1px solid",
        border_color="grey",
        border_radius=".5rem",
        box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        padding="1.3rem",
        max_width="400px"
    )

def network_information_card() -> rx.Component:
    return rx.box(
        rx.box(  # CardHeader
            rx.hstack(
                rx.icon("network", size=20),  # Substitute with the correct icon name if available
                rx.text("Step 2 (Optional): Network Information", size="5", weight="bold"),
                spacing="2",
                align="center"
            ),
            rx.text("Determine your network configuration", size="2", color="gray"),
            margin_bottom="0.8rem"
        ),
        rx.box(  # CardContent
            rx.vstack(
                rx.text("Network Information", as_="label", html_for="local-ip"),
                rx.text("Click one of the buttons to retrieve specific network information", size="2", color="gray"),
                # TODO
                # implement state to call apis and get specific network information--display a list and stuff

                # {
                # "local_ip": "172.18.229.191",
                # "subnet_mask": "255.255.240.0",
                # "cidr": "172.18.229.191/20"
                # }

                # {
                # "windows_host_ip": "130.20.125.77"
                # }

                # rx.input(
                #     id="local-ip",
                #     placeholder="Auto-detect (recommended)",
                #     width="70%",
                #     # value=ProxyState.local_ip,
                #     # on_change=ProxyState.set_local_ip,
                # ),
                # rx.text(
                #     "Leave blank to automatically select your machine's main outbound IP",
                #     size="1",
                #     color="gray",
                # ),
                # spacing="2",
                # align="start",
            ),
            margin_bottom="0.8rem"
        ),
        rx.hstack(  # CardFooter
            rx.button(
                rx.icon("wifi", size=16),
                rx.text("Get Local IP"),
                # on_click=ProxyState.start_proxy,
                # disabled=ProxyState.proxy_status == "running",
                variant="solid"
            ),
            rx.button(
                rx.icon("settings", size=16),
                rx.text("Get Windows Host IP"),
                # on_click=ProxyState.stop_proxy,
                # disabled=ProxyState.proxy_status == "stopped",
                variant="solid"
            ),
            justify="between",
            width="100%"
        ),
        border="1px solid",
        border_color="grey",
        border_radius=".5rem",
        box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        padding="1.3rem",
        # bg="white",
        max_width="400px"
    )


def bacnet_proxy_card():
    return rx.box(
        rx.box(  # CardHeader
            rx.hstack(
                rx.icon("router", size=20),  # Substitute with the correct icon name if available
                rx.text("Step 1: BACnet Proxy", size="5", weight="bold"),
                spacing="2",
                align="center"
            ),
            rx.text("Start or stop the BACnet proxy service", size="2", color="gray"),
            margin_bottom="0.8rem"
        ),
        rx.box(  # CardContent
            rx.vstack(
                rx.text("Local Device Address (Optional)", as_="label", html_for="local-ip"),
                rx.input(
                    id="local_ip",
                    placeholder="Auto-detect (recommended)",
                    width="100%",
                    # value=ProxyState.local_ip,
                    # on_change=ProxyState.set_local_ip,
                ),
                rx.text(
                    "Leave blank to automatically select your machine's main outbound IP",
                    size="1",
                    color="gray",
                ),
                spacing="2",
                align="start",
            ),
            margin_bottom="0.8rem"
        ),
        rx.hstack(  # CardFooter
            rx.button(
                rx.icon("play", size=16),
                rx.text("Start Proxy"),
                # on_click=ProxyState.start_proxy,
                # disabled=ProxyState.proxy_status == "running",
                variant="solid"
            ),
            rx.button(
                rx.icon("square", size=16),
                rx.text("Stop Proxy"),
                # on_click=ProxyState.stop_proxy,
                # disabled=ProxyState.proxy_status == "stopped",
                variant="outline"
            ),
            justify="between",
            width="100%"
        ),
        border="1px solid",
        border_color="grey",
        border_radius=".5rem",
        box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        padding="1.3rem",
        # bg="white",
        max_width="400px"
    )


def bacnet_tool_page_layout(*children) -> rx.Component:
    return rx.grid(

        spacing="6",
        columns="3"
    )

def render() -> rx.Component: return rx.box()

@rx.page(route="/tools/bacnet_scan")
def bacnet_scan_page() -> rx.Component:
    return app_layout_sidebar.app_layout_sidebar(
        bacnet_scan(),
        # render()
    )
