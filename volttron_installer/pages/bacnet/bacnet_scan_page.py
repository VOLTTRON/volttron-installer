import reflex as rx
from ...state import BacnetScanState, ToolState
from ...layouts import app_layout_sidebar
from .bacnet_cards import (
    scan_for_devices_card,
    discovered_devices_card,
    network_information_card,
    bacnet_proxy_card,
    footer,
    device_scan_status,
)
from .bacnet_dialogs import (
    proxy_info_dialog,
    network_info_dialog,
    scan_info_dialog,
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
        # property_operations_card(),
        spacing="6",
        width="100%",
        columns="1"
        # columns={ "base": "1", "md": "2" }
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
    return rx.fragment(
        rx.box(
            # Full page wrapper with scrolling
            rx.box(
                # Centered content container
                rx.vstack(
                    rx.cond(
                        ToolState.running_tools.contains("bacnet_scan_api") == False,
                        rx.fragment(
                            rx.hstack(
                                rx.hstack(
                                    rx.skeleton(height="50px", width="50px", border_radius=".5rem"),
                                    rx.skeleton(height="30px", width="200px", border_radius=".5rem"),
                                    align="center"
                                ),
                                rx.skeleton(height="25px", width="100px", border_radius=".5rem"),
                                justify="between",
                                align="center",
                                width="100%"
                            ),
                            rx.grid(
                                rx.skeleton(width="100%", height="250px", border_radius=".5rem"),
                                rx.skeleton(width="100%", height="250px", border_radius=".5rem"),
                                rx.skeleton(width="100%", height="250px", border_radius=".5rem"),
                                spacing="6",
                                width="100%",
                                columns={ "base": "1", "md": "3" }
                            ),
                            rx.grid(
                                rx.skeleton(width="100%", height="1300px", border_radius=".5rem"),
                                spacing="6",
                                width="100%",
                                columns="1"
                            )
                        ),
                        rx.fragment(
                            bacnet_scan_tool_header(),
                            device_scan_status(),
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
        # Info dialogs
        proxy_info_dialog(),
        network_info_dialog(),
        scan_info_dialog(),
    )


@rx.page(route="/tools/bacnet_scan", on_load=ToolState.start_tool("bacnet_scan_api"))
def bacnet_scan_page() -> rx.Component:
    return app_layout_sidebar.app_layout_sidebar(
        render()
    )