import reflex as rx
from ...state import BacnetScanState
from ...components.form_components import form_entry
from .bacnet_device_table import show_device


def scan_for_devices_card():
    return rx.flex(
        rx.box(  # CardHeader
            rx.hstack(
                rx.icon("search", size=25),
                rx.text("Step 3: Scan for Devices", size="5", weight="bold"),
                rx.spacer(),
                rx.button(
                    rx.icon("info", size=16),
                    on_click=BacnetScanState.show_scan_info,
                    variant="ghost",
                    size="2",
                    color_scheme="blue",
                    border_radius="full",
                    padding="2",
                ),
                spacing="2",
                align="center",
                width="100%"
            ),
            rx.text("Discover BACnet devices on your network", size="2", color="gray"),
            margin_bottom="0.8rem"
        ),
        rx.box(  # CardContent
            rx.vstack(
                rx.text("Subnet Range (CIDR)", as_="label", html_for="local-ip"),
                rx.input(
                    id="network_str",
                    placeholder="e.g. 192.168.1.0/24",
                    width="100%",
                    value=BacnetScanState.scan_ip_range.network_string,
                    on_change=BacnetScanState.scan_ip_range_input,
                ),
                # TODO tie this to a rx.cond, if contains '/' make sure network can sustain pings
                # of the entire range
                rx.cond(
                    BacnetScanState.warn_ping_range,
                    rx.text(
                        "Be sure this network can sustain pings of the entire range",
                        size="1",
                        color="#ffa057",
                        padding="8px 12px",
                        border_radius="6px",
                        background_color="#66350c63"
                    )
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
        rx.flex(  # CardFooter
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
            width="100%",
            margin_top="auto",
        ),
        border="1px solid",
        border_color="grey",
        border_radius=".5rem",
        box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        padding="1.3rem",
        max_width="400px",
        direction="column",
        height="100%"
    )


def discovered_devices_card() -> rx.Component:
    return rx.box(
        rx.box(
            rx.text("Discovered Devices", size="5", weight="bold"),
            rx.cond(
                BacnetScanState.discovered_devices.length() == 0,
                rx.text("No devices discovered yet", color="gray"),
                rx.vstack(
                    rx.text(f"{BacnetScanState.discovered_devices.length()} BACnet devices found", color="gray"),
                    rx.text(f"Click on a device to select and view it's points", size="1", color="gray"),
                    spacing="1"
                )
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
                    height="1000px",
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
                height="1300px",
                overflow_y="auto",
            ),
        ),
        min_height="1400px",
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
    return rx.flex(
        rx.box(  # CardHeader
            rx.hstack(
                rx.icon("network", size=25),
                rx.text("Step 2 (Optional): Network Information", size="5", weight="bold"),
                rx.spacer(),
                rx.button(
                    rx.icon("info", size=16),
                    on_click=BacnetScanState.show_network_info,
                    variant="ghost",
                    size="2",
                    color_scheme="blue",
                    border_radius="full",
                    padding="2",
                ),
                spacing="2",
                align="center",
                width="100%"
            ),
            rx.text("Determine your network configuration", size="2", color="gray"),
            margin_bottom="0.8rem"
        ),
        rx.box(  # CardContent
            rx.vstack(
                rx.text("Network Information", as_="label", html_for="local-ip"),
                rx.cond(
                    BacnetScanState.ip_detection_mode=="",
                    rx.text("Click a button to retrieve network information", size="2", color="gray"),
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
                        rx.cond(
                            BacnetScanState.ip_detection_mode=="local_ip",
                            # Local IP info
                            rx.grid(
                                rx.text("Local IP"),
                                rx.text(BacnetScanState.local_ip_info.local_ip),
                                rx.text("Subnet Mask"),
                                rx.text(BacnetScanState.local_ip_info.subnet_mask),
                                rx.text("CIDR Notation"),
                                rx.text(BacnetScanState.local_ip_info.cidr),
                                columns="2",
                                spacing="2"
                            ),
                            rx.cond(
                                BacnetScanState.ip_detection_mode=="windows_host_ip",
                                # Windows Host IP info
                                rx.grid(
                                    rx.text("Host IP"),
                                    rx.text(BacnetScanState.windows_host_ip_info.address),
                                    columns="2",
                                    spacing="2"
                                ),
                                # Network Discovery info
                                rx.vstack(
                                    rx.cond(
                                        BacnetScanState.is_discovering_networks,
                                        # Loading state
                                        rx.vstack(
                                            rx.hstack(
                                                rx.spinner(size="3"),
                                                rx.text("Discovering networks...", weight="bold"),
                                                spacing="2",
                                                align="center"
                                            ),
                                            rx.text("This may take a few seconds", size="2", color="gray"),
                                            spacing="2",
                                            align="center"
                                        ),
                                        # Results or no results
                                        rx.vstack(
                                            rx.text(
                                                rx.cond(
                                                    BacnetScanState.discovered_networks,
                                                    "Networks discovered",
                                                    "No networks discovered yet"
                                                ),
                                                weight="bold"
                                            ),
                                            rx.cond(
                                                BacnetScanState.discovered_networks,
                                                rx.vstack(
                                                    rx.text("Select a network to scan:", size="2", color="gray"),
                                                    rx.foreach(
                                                        BacnetScanState.discovered_networks,
                                                        lambda network: rx.button(
                                                            rx.hstack(
                                                                rx.icon("wifi", size=16),
                                                                rx.text(network),
                                                                justify="start",
                                                                align="center",
                                                                spacing="2"
                                                            ),
                                                            on_click=BacnetScanState.select_discovered_network(network),
                                                            variant=rx.cond(BacnetScanState.selected_network != network, "outline", "solid"),
                                                            size="2",
                                                            width="100%"
                                                        )
                                                    ),
                                                    spacing="1",
                                                    width="100%"
                                                ),
                                                rx.text("No networks found", size="2", color="red")
                                            ),
                                            spacing="2",
                                            width="100%"
                                        )
                                    ),
                                    spacing="2",
                                    width="100%"
                                )
                            )
                        )
                    )
                ),
            ),
            margin_bottom="0.8rem"
        ),
        rx.flex(  # CardFooter
            rx.button(
                rx.cond(
                    (BacnetScanState.ip_detection_mode=="windows_host_ip") &
                    (BacnetScanState.pinging_ip),
                    rx.spinner(),
                    rx.icon("settings", size=16),
                ),
                rx.text("Get Host IP", white_space="nowrap"),
                on_click=lambda: BacnetScanState.set_ip_detection_mode("windows_host_ip"),
                disabled=rx.cond(
                    (BacnetScanState.pinging_ip) | (BacnetScanState.proxy_up == False),
                    True,
                    False
                ),
                variant="outline",
                flex="1 0 auto",
                justify="center",
            ),
            rx.button(
                rx.cond(
                    (BacnetScanState.ip_detection_mode=="network_discovery") &
                    (BacnetScanState.pinging_ip),
                    rx.spinner(),
                    rx.icon("wifi", size=16),
                ),
                rx.text("Discover Networks", white_space="nowrap"),
                on_click=lambda: BacnetScanState.set_ip_detection_mode("network_discovery"),
                disabled=rx.cond(
                    (BacnetScanState.pinging_ip) | (BacnetScanState.proxy_up == False),
                    True,
                    False
                ),
                variant="solid",
                flex="1 0 auto",
                justify="center",
            ),
            width="100%",
            wrap="wrap",
            spacing="3",
            margin_top="auto",
        ),
        border="1px solid",
        border_color="grey",
        border_radius=".5rem",
        box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        padding="1.3rem",
        # bg="white",
        max_width="400px",
        direction="column",
        height="100%"
    )


def bacnet_proxy_card():
    return rx.flex(
        rx.box(  # CardHeader
            rx.hstack(
                rx.icon("router", size=25),  # Substitute with the correct icon name if available
                rx.text("Step 1: BACnet Proxy", size="5", weight="bold"),
                rx.spacer(),
                rx.button(
                    rx.icon("info", size=16),
                    on_click=BacnetScanState.show_proxy_info,
                    variant="ghost",
                    size="2",
                    color_scheme="blue",
                    border_radius="full",
                    padding="2",
                ),
                spacing="2",
                align="center",
                width="100%"
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
                    read_only=rx.cond(
                            BacnetScanState.proxy_up,
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
        rx.flex(  # CardFooter
            rx.button(
                rx.cond(
                    BacnetScanState.is_starting_proxy,
                    rx.spinner(),
                    rx.icon("play", size=16)
                ),
                rx.text("Start Proxy", white_space="nowrap"),
                on_click=BacnetScanState.toggle_proxy,
                disabled=rx.cond(
                    BacnetScanState.proxy_up,
                    True,
                    False
                ),
                variant="solid",
                flex="1 0 auto",
                justify="center",
            ),
            rx.button(
                rx.icon("square", size=16),
                rx.text("Stop Proxy", white_space="nowrap"),
                on_click=BacnetScanState.toggle_proxy,
                disabled=rx.cond(
                    BacnetScanState.proxy_up,
                    False,
                    True
                ),
                variant="outline",
                flex="1 0 auto",
                justify="center",
            ),
            width="100%",
            wrap="wrap",
            spacing="3",
            margin_top="auto",
        ),
        border="1px solid",
        border_color="grey",
        border_radius=".5rem",
        box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        padding="1.3rem",
        # bg="white",
        max_width="400px",
        direction="column",
        height="100%"
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


def device_scan_status() -> rx.Component:
    return rx.fragment(
            rx.foreach(
                BacnetScanState.all_device_scan_point_status,
                lambda status: rx.callout.root(
                    rx.hstack(
                        rx.callout.icon(rx.icon("info")),
                        rx.vstack(
                            rx.text(f"Scanning points on device: {status.object_name}"),
                            rx.progress(
                                value=status.percent_finished,
                            ),
                            rx.text(status.message, size="1"),
                            width="100%"
                        ),
                        align="center"
                    )
                )
            )
        )