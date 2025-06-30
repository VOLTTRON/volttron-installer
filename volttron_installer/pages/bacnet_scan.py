import reflex as rx
from ..state import BacnetScanState, ToolState
from ..components.form_components import form_entry
from ..layouts import app_layout_sidebar

def scan_for_devices_card():
    return rx.box(
        rx.box(  # CardHeader
            rx.hstack(
                rx.icon("search", size=25),
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
                    value=BacnetScanState.scan_ip_range.network_string,
                    on_change=BacnetScanState.scan_ip_range_input,
                ),
                rx.text(
                    "Use the network information from Step 2 or enter manually",
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
                rx.cond(
                    BacnetScanState.scanning_bacnet_range,
                    rx.spinner(),
                    rx.icon("search", size=16)
                ),
                rx.text("Scan for Devices"),
                on_click=BacnetScanState.handle_scan_ip_range,
                disabled=rx.cond(
                    (BacnetScanState.proxy_up == False) |
                    (BacnetScanState.scanning_bacnet_range),
                    True,
                    False
                ),
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
        max_width="400px"
    )

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

def show_device(device: dict[str, str], index: str) -> rx.Component:
    return rx.table.row(
        rx.table.cell(device["name"]),
        rx.table.cell(device["id"]),
        rx.table.cell(device["address"]),
        class_name=rx.cond(
            BacnetScanState.selected_device["id"] == device["id"],
            "csv_data_cell active",
            "csv_data_cell"
        ),
        on_click = lambda: BacnetScanState.handle_device_row_click(index)
    )

def discovered_devices_card() -> rx.Component:
    return rx.box(
        rx.box(
            rx.text("Discovered Devices", size="5", weight="bold"),
            rx.cond(
                BacnetScanState.discovered_devices.length() == 0,
                rx.text("No devices discovered yet", color="gray"),
                rx.text(f"{BacnetScanState.discovered_devices.length()} BACnet devices found", color="gray")
            ),
            margin_bottom="1em",
        ),
        rx.cond(
            BacnetScanState.discovered_devices.length() == 0,
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
                            BacnetScanState.discovered_devices,
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
            rx.text("Input a known device or scan and select a discovered device to access read and write properties", size="2", color="gray"),
            margin_bottom="1rem"
        ),
        rx.tabs(
            rx.tabs.list(
                rx.tabs.trigger("Read Property", value="read"),
                rx.tabs.trigger("Write Property", value="write"),
                spacing="2",
                width="100%",
                justify="center",
                align="center",
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
                            value=BacnetScanState.read_property.device_address,
                            on_change=lambda v: BacnetScanState.read_property_input("device_address", v),
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Object Identifier",
                        rx.input(
                            id="read_object_identifier",
                            placeholder="e.g., device,506892",
                            value=BacnetScanState.read_property.object_identifier,
                            on_change=lambda v: BacnetScanState.read_property_input("object_identifier", v),
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Property Identifier",
                        rx.input(
                            id="read_property_identifier",
                            value=BacnetScanState.read_property.property_identifier,
                            on_change=lambda v: BacnetScanState.read_property_input("property_identifier", v),
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
                            value=BacnetScanState.read_property.property_array_index,
                            on_change=lambda v: BacnetScanState.read_property_input("property_array_index", v),
                            width="100%",
                            type="number"
                        ),
                    ),
                    rx.button(
                        "Read Property",
                        width="100%",
                        disabled=rx.cond(
                            (BacnetScanState.is_read_property_valid==False) | (BacnetScanState.proxy_up==False),
                            True,
                            False
                        ),
                        # TODO on click read property
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
                            value=BacnetScanState.write_property.device_address,
                            on_change=lambda v: BacnetScanState.write_property_input("device_address", v),
                            width="100%",
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Object Identifier",
                        rx.input(
                            id="write_object_identifier",
                            placeholder="e.g., device,506892",
                            width="100%",
                            value=BacnetScanState.write_property.object_identifier,
                            on_change=lambda v: BacnetScanState.write_property_input("object_identifier", v),
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Property Identifier",
                        rx.input(
                            id="write_property_identifier",
                            placeholder="e.g., description",
                            width="100%",
                            value=BacnetScanState.write_property.property_identifier,
                            on_change=lambda v: BacnetScanState.write_property_input("property_identifier", v),
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Value",
                        rx.input(
                            id="write_value",
                            placeholder="e.g., some value",
                            width="100%",
                            value=BacnetScanState.write_property.value,
                            on_change=lambda v: BacnetScanState.write_property_input("value", v),
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Priority",
                        rx.input(
                            id="write_priority",
                            placeholder="eg., 1",
                            width="100%",
                            type="number",
                            value=BacnetScanState.write_property.priority,
                            on_change=lambda v: BacnetScanState.write_property_input("priority", v),
                        ),
                        required_entry=True,
                    ),
                    form_entry.form_entry(
                        "Property Array Index (Optional)",
                        rx.input(
                            id="write_property_array_index",
                            placeholder="eg., 1",
                            width="100%",
                            type="number",
                            value=BacnetScanState.write_property.property_array_index,
                            on_change=lambda v: BacnetScanState.write_property_input("property_array_index", v),
                        ),
                    ),
                    rx.button(
                        "Write Property",
                        width="100%",
                        disabled=rx.cond(
                            (BacnetScanState.is_write_property_valid==False) | (BacnetScanState.proxy_up==False),
                            True,
                            False
                        )
                        # TODO onclick = write property
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
    )

def network_information_card() -> rx.Component:
    return rx.box(
        rx.box(  # CardHeader
            rx.hstack(
                rx.icon("network", size=25),
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
                rx.cond(
                    BacnetScanState.ip_detection_mode=="",
                    rx.text("Click one of the buttons to retrieve specific network information", size="2", color="gray"),
                    rx.cond(
                        BacnetScanState.pinging_ip,
                        rx.hstack(
                            rx.spinner(
                                width="30px",
                                height="30px"
                            ),
                            width="100%",
                            height="100%",
                            align="center",
                            justify="center"
                        ),
                        rx.grid(
                            rx.cond(
                                BacnetScanState.ip_detection_mode=="local_ip",
                                # Local IP info
                                rx.fragment(
                                    rx.text("Local IP"),
                                    rx.text(BacnetScanState.local_ip_info.local_ip),
                                    rx.text("Subnet Mask"),
                                    rx.text(BacnetScanState.local_ip_info.subnet_mask),
                                    rx.text("CIDR Notation"),
                                    rx.text(BacnetScanState.local_ip_info.cidr)
                                ),
                                # Windows Host IP info
                                rx.fragment(
                                    rx.text("Windows Host IP"),
                                    rx.text(BacnetScanState.windows_host_ip_info.windows_host_ip),
                                )
                            ),
                            columns="2",
                            spacing="2"
                        )
                    )
                ),
            ),
            margin_bottom="0.8rem"
        ),
        rx.hstack(  # CardFooter
            rx.button(
                rx.cond(
                    (BacnetScanState.ip_detection_mode=="local_ip") & 
                    (BacnetScanState.pinging_ip),
                    rx.spinner(),    
                    rx.icon("wifi", size=16),
                ),
                rx.text("Get Local IP"),
                on_click=lambda: BacnetScanState.set_ip_detection_mode("local_ip"),
                disabled=rx.cond(
                    (BacnetScanState.pinging_ip) | (BacnetScanState.proxy_up == False),
                    True,
                    False
                ),
                variant="solid"
            ),
            rx.button(
                rx.cond(
                    (BacnetScanState.ip_detection_mode=="windows_host_ip") & 
                    (BacnetScanState.pinging_ip),
                    rx.spinner(),
                    rx.icon("settings", size=16),
                ),
                rx.text("Get Windows Host IP"),
                on_click=lambda: BacnetScanState.set_ip_detection_mode("windows_host_ip"),
                disabled=rx.cond(
                    (BacnetScanState.pinging_ip) | (BacnetScanState.proxy_up == False),
                    True,
                    False
                ),
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
                rx.icon("router", size=25),  # Substitute with the correct icon name if available
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
                    disabled=rx.cond(
                            (BacnetScanState.proxy_up) | (BacnetScanState.is_starting_proxy),
                            True,
                            False
                        ),
                    value=BacnetScanState.proxy_field_value,
                    on_change=BacnetScanState.handle_proxy_field_edit,
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
                rx.cond(
                    BacnetScanState.is_starting_proxy,
                    rx.spinner(),
                    rx.icon("play", size=16)
                ),
                rx.text("Start Proxy"),
                on_click=BacnetScanState.toggle_proxy,
                disabled=rx.cond(
                    BacnetScanState.proxy_up,
                    True,
                    False
                ),
                variant="solid"
            ),
            rx.button(
                rx.icon("square", size=16),
                rx.text("Stop Proxy"),
                on_click=BacnetScanState.toggle_proxy,
                disabled=rx.cond(
                    BacnetScanState.proxy_up,
                    False,
                    True
                ),
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

def footer():
    return rx.el.footer(
        rx.box(
            rx.hstack(
                rx.box(
                    rx.text("Proxy Status: "),
                    rx.cond(
                        BacnetScanState.proxy_up,
                        rx.text(
                            "Running",
                            class_name="text-green-500 font-medium",  # or "text-gray-500 font-medium"
                        ),
                        rx.text(
                            "Offline",
                            class_name="text-red-500 font-medium",  # or "text-gray-500 font-medium"
                        ),
                    )
                ),
                rx.cond(
                    BacnetScanState.discovered_devices.length() == 0,
                    rx.text("No devices discovered"),
                    rx.text(f"{BacnetScanState.discovered_devices.length()} devices discovered")
                ),
                justify="between",
                align="center",
                class_name="text-sm text-muted-foreground",
                width="100%",
            ),
            class_name="flex",
        ),
        class_name="mt-8 border-t pt-4",
    )

def bacnet_networking_grid() -> rx.Component:
    return rx.grid(
        bacnet_proxy_card(),
        network_information_card(),
        scan_for_devices_card(),
        spacing="6",
        width="100%",
        columns={ "base": "1", "md": "3" }
    )

def bacnet_device_and_property_grid() -> rx.Component:
    return rx.grid(
        discovered_devices_card(),
        property_operations_card(),
        spacing="6",
        width="100%",
        columns={ "base": "1", "md": "2" }
    )

def bacnet_scan_tool_header() -> rx.Component:
    return rx.hstack(
        rx.hstack(
            rx.icon("server", size=20),
            rx.text("BACnet Scan Tool", size="5", weight="bold"),
            align="center"
        ),
        rx.cond(
            BacnetScanState.proxy_up,
            rx.badge(
                "Proxy Running",
                color_scheme="green"
            ),
            rx.badge(
                "Proxy Offline",
                color_scheme="red"
            ),
        ),
        justify="between"
    )

def proxy_down_warning() -> rx.Component:
    return rx.cond(
        BacnetScanState.proxy_up==False,
        rx.callout(
            "A proxy must be running to use this tool.",
            icon="triangle-alert",
            color_scheme="red",
            role="alert"
        )
    )

def render() -> rx.Component:
    return (
        rx.box(
            # Full page wrapper with scrolling
            rx.box(
                # Centered content container
                rx.vstack(
                    rx.cond(
                        ToolState.running_tools.contains("bacnet_scan_tool") == False,
                        rx.fragment(
                            rx.grid(
                                rx.skeleton(width="100%"),
                                rx.skeleton(width="100%"),
                                spacing="6",
                                width="100%",
                                columns={ "base": "1", "md": "2" }
                            ),
                            rx.grid(
                                rx.skeleton(width="100%"),
                                rx.skeleton(width="100%"),
                                rx.skeleton(width="100%"),
                                spacing="6",
                                width="100%",
                                columns={ "base": "1", "md": "3" }      
                            )
                        ),
                        rx.fragment(
                            bacnet_scan_tool_header(),
                            proxy_down_warning(),
                            bacnet_networking_grid(),
                            bacnet_device_and_property_grid(),
                            footer(),
                        ),
                    ),
                    spacing="6",
                    align_items="stretch",
                ),
                max_width="1200px",
                margin_left="auto",
                margin_right="auto",
                padding_y="1.5rem",
            ),
            height="100vh",  # Full viewport height
            width="100%",    # Full width
            overflow_y="auto", # Scrolling applied to full width
            padding_x="16px"
        ),

    )


@rx.page(route="/tools/bacnet_scan", on_load=ToolState.start_tool("bacnet_scan_tool"))
def bacnet_scan_page() -> rx.Component:
    return app_layout_sidebar.app_layout_sidebar(
        render()
    )
