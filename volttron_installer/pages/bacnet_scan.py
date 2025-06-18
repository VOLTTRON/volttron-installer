import reflex as rx
from ..state import BacnetScanState
from ..components.form_components import form_entry
from ..layouts import app_layout_sidebar

def bacnet_scan() -> rx.Component:
    return rx.fragment(
        rx.vstack(
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
            ),
            padding_top="2rem",
            align="center",
            justify="center",
            width="100%",
        )
    )

def bacnet_scan_page() -> rx.Component:
    return app_layout_sidebar.app_layout_sidebar(
        bacnet_scan(),
    )
