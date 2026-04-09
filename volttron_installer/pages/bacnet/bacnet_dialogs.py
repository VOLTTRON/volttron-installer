import reflex as rx
from ...state import BacnetScanState, PlatformPageState
from ...components.form_components import form_entry
from ...components.tiles import platform_tile
from .bacnet_device_table import (
    show_selected_points_table,
    selected_points_pagination,
)


def export_points_dialog() -> rx.Component:
    return rx.dialog.root(
            rx.dialog.trigger(
                rx.button(
                    rx.hstack(
                        rx.icon("upload", size=15),
                        rx.text("Export to CSV"),
                        align="center",
                        justify="center",
                        spacing="2"
                    ),
                    size="1",
                    disabled=rx.cond(
                        BacnetScanState.selected_points.length() == 0,
                        True,
                        False
                    )
                )
            ),
            rx.dialog.content(
                rx.dialog.title("CSV Contents"),
                rx.dialog.description(f"{BacnetScanState.selected_points.length()} points selected for exporting."),
                rx.inset(
                    show_selected_points_table(),
                    side="x",
                    margin_top="24px",
                    margin_bottom="24px",
                ),
                rx.vstack(
                    selected_points_pagination(),
                    rx.hstack(
                        rx.dialog.close(
                            rx.button(
                                "Close",
                                color_scheme="gray",
                                variant="soft",
                                size="2"
                            ),
                        ),
                        rx.dialog.close(
                            rx.button(
                                "Export to CSV",
                                variant="soft",
                                size="2",
                                on_click=lambda: BacnetScanState.export_to_csv
                            ),
                        ),
                        width="100%",
                        justify="end",
                        spacing="2"
                    ),
                    spacing="6",
                    width="100%"
                ),
                on_close_auto_focus=lambda: BacnetScanState.on_selected_points_dialog_close,
                max_width="100rem",
                width="clamp(20rem, 80vw, 100rem)",
            )
        )


def add_to_registry_config_file_dialog() -> rx.Component:
    return rx.fragment(
        rx.dialog.root(
            rx.dialog.trigger(
                rx.button(
                    rx.hstack(
                        rx.icon("plus", size=15),
                        rx.text("Create a Registry Config File"),
                        align="center",
                        spacing="2"
                    ),
                    size="1",
                    disabled=rx.cond(
                        BacnetScanState.selected_points.length() == 0,
                        True,
                        False
                    ),
                    on_click=BacnetScanState.open_registry_dialog,
                )
            ),
            rx.dialog.content(
                rx.dialog.title("Registry Config File Contents"),
                rx.dialog.description(
                    f"{BacnetScanState.selected_points.length()} points selected to create a registry config file."
                ),
                rx.inset(
                    show_selected_points_table(),
                    side="x",
                    margin_top="24px",
                    margin_bottom="24px",
                ),
                rx.vstack(
                    selected_points_pagination(),
                    rx.hstack(
                        rx.button(
                            "Close",
                            color_scheme="gray",
                            variant="soft",
                            size="2",
                            on_click=BacnetScanState.close_dialogs,
                        ),
                        rx.button(
                            "Add to Registry Config File",
                            variant="soft",
                            size="2",
                            on_click=BacnetScanState.open_select_platform_dialog,
                        ),
                        width="100%",
                        justify="end",
                        spacing="2"
                    ),
                    spacing="6",
                    width="100%"
                ),
                max_width="100rem",
                width="clamp(20rem, 80vw, 100rem)",
            ),
            open=BacnetScanState.dialog_registry_open,
        ),

        # Selecting Platforms Dialog
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Select a Platform"),
                rx.dialog.description("Select a platform to add the registry config file to."),
                rx.form(
                    # Replace the simple grid with a grid that has custom column widths
                    rx.grid(
                        # First column (70%) - Platform listings
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.foreach(
                                        PlatformPageState.in_file_platforms,
                                        lambda platform: platform_tile.platform_tile(
                                            platform.platform.config.instance_name,
                                            platform,
                                            background_color=rx.cond(
                                                BacnetScanState.selected_platform_uid == platform.platform.config.instance_name,
                                                "#44C0ED",
                                                "rgba(145, 145, 145, 0.29)"
                                            ),
                                            on_click=lambda: BacnetScanState.select_platform_for_registry_config(platform.platform.config.instance_name)
                                        )
                                    ),
                                    wrap="wrap",
                                    spacing="6",
                                    padding="1rem",
                                    margin_top="24px",
                                ),
                                rx.cond(
                                    BacnetScanState.platform_has_platform_driver == False,
                                    rx.text(
                                        "This selected platform doesn't already contain a platform.driver agent, confirming will automatically add a platform.driver agent to the platform along side the registry config within it's config store.",
                                        size="1",
                                        color="#ffa057",
                                        padding="8px 12px",
                                        border_radius="6px",
                                        background_color="#66350c63",
                                        margin_button="24px",
                                    )
                                ),
                                width="100%",  # Take full width of this grid cell
                                spacing="3"
                            ),
                            width="100%",  # Take full width of this grid cell,
                        ),

                        # Second column (30%) - Form entry
                        rx.box(
                            form_entry.form_entry(
                                "Path",
                                rx.input(
                                    placeholder="Provide a path to save the registry config file",
                                    # width="100%",  # Modified to take full width of its container
                                    default_value="points.csv",
                                    name="path",
                                    disabled=rx.cond(
                                        BacnetScanState.selected_platform_uid == "",
                                        True,
                                        False
                                    ),
                                    required=True,
                                ),
                                required_entry=True,
                            ),
                            width="100%",  # Take full width of this grid cell
                            margin_top="24px",
                        ),

                        # Define custom grid template columns for the 70/30 split
                        template_columns={"base": "1fr", "md": "70% 30%"},
                        gap="4",
                        width="100%",
                    ),

                    rx.hstack(
                        rx.button(
                            "Cancel",
                            color_scheme="gray",
                            variant="soft",
                            size="2",
                            on_click=BacnetScanState.close_dialogs,
                        ),
                        rx.button(
                            "Confirm",
                            color_scheme="green",
                            variant="soft",
                            size="2",
                            type="submit",
                            disabled=rx.cond(
                                BacnetScanState.selected_platform_uid == "",
                                True,
                                False
                            ),
                        ),
                        width="100%",
                        justify="end",
                        spacing="2"
                    ),
                    on_submit=BacnetScanState.on_add_to_registry_config_confirm
                ),
                max_width="100rem",
                width="clamp(20rem, 80vw, 100rem)",
            ),
            open=BacnetScanState.dialog_select_platform_open,
        ),
    )


def proxy_info_dialog():
    """Info dialog for BACnet Proxy card."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon("router", size=24),
                    rx.text("BACnet Proxy Information", size="5", weight="bold"),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            rx.icon("x", size=16),
                            variant="ghost",
                            size="2",
                        )
                    ),
                    align="center",
                    width="100%"
                ),
                rx.separator(),
                rx.vstack(
                    rx.text("What is the BACnet Proxy?", weight="bold", size="3"),
                    rx.text(
                        "The BACnet proxy service acts as a communication bridge between your network and BACnet devices. "
                        "It handles the low-level BACnet protocol communication and provides a standardized interface for device discovery and data access.",
                        color="gray"
                    ),
                    rx.text("Key Features:", weight="bold", size="3", margin_top="1rem"),
                    rx.vstack(
                        rx.text("• Handles BACnet/IP communication protocols"),
                        rx.text("• Manages device discovery and enumeration"),
                        rx.text("• Provides secure access to device properties"),
                        rx.text("• Supports both read and write operations"),
                        spacing="1",
                        margin_left="1rem"
                    ),
                    rx.text("Configuration:", weight="bold", size="3", margin_top="1rem"),
                    rx.text(
                        "You can optionally specify a local device address to bind the proxy to a specific network interface. "
                        "If left blank, the proxy will automatically detect and use the appropriate network interface.",
                        color="gray"
                    ),
                    spacing="3",
                    align="start"
                ),
                spacing="4",
                width="100%",
            ),
            max_width="600px"
        ),
        open=BacnetScanState.show_proxy_info_dialog,
        on_open_change=BacnetScanState.hide_proxy_info
    )


def network_info_dialog():
    """Info dialog for Network Information card."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon("network", size=24),
                    rx.text("Network Information", size="5", weight="bold"),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            rx.icon("x", size=16),
                            variant="ghost",
                            size="2",
                        )
                    ),
                    align="center",
                    width="100%"
                ),
                rx.separator(),
                rx.vstack(
                    rx.text("How Network Discovery Works", weight="bold", size="3"),
                    rx.text(
                        "The network discovery system uses multiple techniques to intelligently identify active networks "
                        "where BACnet devices might be located. This comprehensive approach maximizes the chances of finding all accessible networks.",
                        color="gray"
                    ),
                    rx.text("Discovery Process:", weight="bold", size="3", margin_top="1rem"),
                    rx.vstack(
                        rx.text("1. Router Table Analysis: Examines the system's routing table to identify all network interfaces and their associated IP ranges"),
                        rx.text("2. ARP Table Inspection: Reviews the Address Resolution Protocol (ARP) table to find recently active devices and their networks"),
                        rx.text("3. Common Range Detection: Checks for standard private IP ranges (192.168.x.x, 10.x.x.x, 172.16-31.x.x) and common subnets"),
                        rx.text("4. Network Validation: Pings common gateway addresses (x.x.x.1, x.x.x.254) on each discovered network to verify connectivity"),
                        rx.text("5. Live Network Filtering: Returns only networks that respond to ping tests, indicating active infrastructure"),
                        spacing="1",
                        margin_left="1rem"
                    ),
                    rx.text("Alternative Methods:", weight="bold", size="3", margin_top="1rem"),
                    rx.vstack(
                        rx.text("• Get Host IP: Quick method that retrieves your system's primary IP address and estimates the local network range"),
                        rx.text("• Manual Entry: Direct input of known network ranges in CIDR notation (e.g., 192.168.1.0/24)"),
                        spacing="1",
                        margin_left="1rem"
                    ),
                    rx.text("Benefits:", weight="bold", size="3", margin_top="1rem"),
                    rx.text(
                        "This multi-layered approach ensures you don't miss BACnet devices on secondary networks, VLANs, or "
                        "virtual interfaces that might not be obvious from a simple IP address lookup.",
                        color="gray"
                    ),
                    spacing="3",
                    align="start"
                ),
                spacing="4",
                width="100%",
            ),
            max_width="600px"
        ),
        open=BacnetScanState.show_network_info_dialog,
        on_open_change=BacnetScanState.hide_network_info
    )


def scan_info_dialog():
    """Info dialog for Scan for Devices card."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon("search", size=24),
                    rx.text("Scan for Devices Information", size="5", weight="bold"),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            rx.icon("x", size=16),
                            variant="ghost",
                            size="2",
                        )
                    ),
                    align="center",
                    width="100%"
                ),
                rx.separator(),
                rx.vstack(
                    rx.text("Advanced BACnet Device Discovery", weight="bold", size="3"),
                    rx.text(
                        "The scanning system employs a sophisticated multi-tier approach to maximize device discovery, "
                        "automatically falling back through different methods if initial attempts fail.",
                        color="gray"
                    ),
                    rx.text("Pre-Scan Router Discovery:", weight="bold", size="3", margin_top="1rem"),
                    rx.text(
                        "• Who-Is-Router-To-Network: First attempts to discover BACnet routers that might bridge to other networks, "
                        "ensuring devices on remote BACnet networks aren't missed",
                        margin_left="1rem"
                    ),
                    rx.text("Tier 1 - BACpypes3 Broadcast Scan:", weight="bold", size="3", margin_top="1rem"),
                    rx.vstack(
                        rx.text("• Uses the BACpypes3 library's native Who-Is broadcast mechanism"),
                        rx.text("• Sends properly formatted BACnet Who-Is requests to the broadcast address"),
                        rx.text("• Listens for I-Am responses from compliant BACnet/IP devices"),
                        rx.text("• Most efficient method for standard BACnet implementations"),
                        spacing="1",
                        margin_left="1rem"
                    ),
                    rx.text("Tier 2 - Manual Broadcast Scan:", weight="bold", size="3", margin_top="1rem"),
                    rx.vstack(
                        rx.text("• Fallback method using custom UDP broadcast implementation"),
                        rx.text("• Manually constructs BACnet APDU packets without BACpypes3 dependencies"),
                        rx.text("• Uses raw socket programming to send Who-Is requests"),
                        rx.text("• Handles networks where BACpypes3 broadcast might fail due to routing or firewall issues"),
                        spacing="1",
                        margin_left="1rem"
                    ),
                    rx.text("Tier 3 - Brute Force Unicast Scan:", weight="bold", size="3", margin_top="1rem"),
                    rx.vstack(
                        rx.text("• Last resort method for problematic networks"),
                        rx.text("• Only triggered if broadcast methods find fewer than 3 devices"),
                        rx.text("• Sends individual Who-Is requests to every IP address in the specified range"),
                        rx.text("• Bypasses broadcast limitations in segmented or filtered networks"),
                        rx.text("• Slower but ensures maximum coverage, especially for devices behind firewalls"),
                        rx.text("• Can be disabled via the enable_brute_force parameter"),
                        spacing="1",
                        margin_left="1rem"
                    ),
                    rx.text("Why This Approach:", weight="bold", size="3", margin_top="1rem"),
                    rx.text(
                        "Different networks have varying configurations, security policies, and infrastructure. "
                        "This tiered approach ensures device discovery works in enterprise environments, "
                        "segmented networks, and even misconfigured systems where standard broadcasts might fail.",
                        color="gray"
                    ),
                    rx.text("Targeted Scanning Tips:", weight="bold", size="3", margin_top="1rem"),
                    rx.vstack(
                        rx.text("• For known device IPs, use /32 for instant scanning: 192.168.1.248/32"),
                        rx.text("• Smaller subnets scan faster and reduce network load"),
                        rx.text("• Use network discovery in Step 2 to identify optimal scan ranges"),
                        spacing="1",
                        margin_left="1rem"
                    ),
                    rx.text("Subnet Size Reference:", weight="bold", size="3", margin_top="1rem"),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("CIDR"),
                                rx.table.column_header_cell("Subnet Mask"),
                                rx.table.column_header_cell("IP Count"),
                                rx.table.column_header_cell("Use Case"),
                            )
                        ),
                        rx.table.body(
                            rx.table.row(
                                rx.table.cell("/32"),
                                rx.table.cell("255.255.255.255"),
                                rx.table.cell("1"),
                                rx.table.cell("Single device"),
                            ),
                            rx.table.row(
                                rx.table.cell("/30"),
                                rx.table.cell("255.255.255.252"),
                                rx.table.cell("4"),
                                rx.table.cell("Point-to-point links"),
                            ),
                            rx.table.row(
                                rx.table.cell("/28"),
                                rx.table.cell("255.255.255.240"),
                                rx.table.cell("16"),
                                rx.table.cell("Small device groups"),
                            ),
                            rx.table.row(
                                rx.table.cell("/24"),
                                rx.table.cell("255.255.255.0"),
                                rx.table.cell("256"),
                                rx.table.cell("Typical local networks"),
                            ),
                            rx.table.row(
                                rx.table.cell("/16"),
                                rx.table.cell("255.255.0.0"),
                                rx.table.cell("65,536"),
                                rx.table.cell("Large enterprise networks"),
                            ),
                        ),
                        size="1",
                        margin_left="1rem",
                        margin_top="0.5rem"
                    ),
                    rx.box(
                        rx.hstack(
                            rx.icon("triangle_alert", size=16, color="orange"),
                            rx.text("Warning: ", weight="bold", color="orange"),
                            rx.text("Large subnets (/16, /8) may take significant time and network resources. Consider using smaller ranges or targeted scans.", color="gray"),
                            spacing="1",
                            align="center"
                        ),
                        background_color="#fff3cd",
                        border="1px solid #ffeaa7",
                        border_radius="4px",
                        padding="0.75rem",
                        margin_left="1rem",
                        margin_top="0.5rem"
                    ),
                    rx.text(
                        "Learn more about CIDR notation and subnetting: ",
                        rx.link("RFC 4632 (CIDR)", href="https://tools.ietf.org/html/rfc4632", is_external=True, color="blue"),
                        margin_left="1rem",
                        margin_top="0.5rem",
                        size="2",
                        color="gray"
                    ),
                    spacing="3",
                    align="start"
                ),
                spacing="4",
                width="100%",
            ),
            max_width="600px"
        ),
        open=BacnetScanState.show_scan_info_dialog,
        on_open_change=BacnetScanState.hide_scan_info
    )