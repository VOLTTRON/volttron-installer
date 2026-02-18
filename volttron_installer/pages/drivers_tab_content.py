"""
Drivers Tab Content - UI for managing platform drivers
"""

import reflex as rx
from ..states.driver_management import DriverManagementState as State


def drivers_tab_content() -> rx.Component:
    """Main drivers tab content with driver list and management controls"""
    return rx.vstack(
        # Header with add button
        rx.hstack(
            rx.heading("Platform Drivers", size="6"),
            rx.hstack(
                rx.cond(
                    State.platform_driver_exists,
                    rx.button(
                        rx.icon("upload"),
                        "Deploy Configs",
                        on_click=State.deploy_driver_configs,
                        size="2",
                        variant="soft",
                        color_scheme="green",
                        loading=State._deploying_configs,
                    ),
                ),
                rx.cond(
                    State.platform_driver_exists,
                    rx.button(
                        rx.icon("plus"),
                        "Add Driver",
                        on_click=State.open_add_driver_dialog,
                        size="2",
                    ),
                    rx.callout.root(
                        rx.callout.icon(rx.icon("info")),
                        rx.callout.text(
                            "Install platform.driver agent to manage drivers"
                        ),
                        size="1",
                        variant="soft",
                        color_scheme="blue",
                    ),
                ),
                spacing="2",
            ),
            justify="between",
            width="100%",
            align="center",
        ),
        
        # Driver list or empty state
        rx.cond(
            State.drivers_count > 0,
            rx.vstack(
                rx.foreach(
                    State.driver_configs,
                    driver_card
                ),
                spacing="3",
                width="100%",
            ),
            rx.box(
                rx.vstack(
                    rx.icon("database", size=48, color="gray"),
                    rx.text(
                        "No drivers configured",
                        size="4",
                        color="gray",
                        weight="medium",
                    ),
                    rx.text(
                        "Add a driver to start collecting device data",
                        size="2",
                        color="gray",
                    ),
                    spacing="2",
                    align="center",
                ),
                padding="4rem",
                width="100%",
            ),
        ),
        
        # Dialogs
        add_driver_dialog(),
        edit_driver_dialog(),
        delete_driver_dialog(),
        
        spacing="4",
        width="100%",
        padding="1rem",
    )


def driver_card(driver: dict) -> rx.Component:
    """Display card for a single driver configuration"""
    return rx.card(
        rx.vstack(
            # Header row with path and actions
            rx.hstack(
                rx.vstack(
                    rx.text(
                        rx.code(f"{driver['campus']}/{driver['building']}/{driver['unit']}"),
                        weight="bold",
                        size="4",
                    ),
                    rx.hstack(
                        rx.badge(
                            driver["driver_type"],
                            variant="soft",
                            color_scheme="blue",
                        ),
                        rx.text(
                            f"Interval: {driver['interval']}s",
                            size="2",
                            color="gray",
                        ),
                        spacing="2",
                    ),
                    spacing="1",
                    align_items="start",
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("pencil", size=16),
                        on_click=lambda: State.open_edit_driver_dialog(driver["path"]),
                        size="2",
                        variant="soft",
                        color_scheme="gray",
                    ),
                    rx.button(
                        rx.icon("trash-2", size=16),
                        on_click=lambda: State.open_delete_driver_dialog(
                            driver["path"], driver["config_id"]
                        ),
                        size="2",
                        variant="soft",
                        color_scheme="red",
                    ),
                    spacing="2",
                ),
                justify="between",
                width="100%",
                align="center",
            ),
            
            # Details row
            rx.divider(),
            rx.hstack(
                rx.vstack(
                    rx.text("Registry", size="1", color="gray", weight="medium"),
                    rx.text(driver["registry"], size="2"),
                    spacing="1",
                    align_items="start",
                ),
                rx.vstack(
                    rx.text("Timezone", size="1", color="gray", weight="medium"),
                    rx.text(driver["timezone"], size="2"),
                    spacing="1",
                    align_items="start",
                ),
                rx.cond(
                    driver.get("heart_beat_point", "") != "",
                    rx.vstack(
                        rx.text("Heartbeat Point", size="1", color="gray", weight="medium"),
                        rx.text(driver.get("heart_beat_point", ""), size="2"),
                        spacing="1",
                        align_items="start",
                    ),
                ),
                spacing="6",
                wrap="wrap",
            ),
            
            spacing="3",
            width="100%",
        ),
        width="100%",
    )


def add_driver_dialog() -> rx.Component:
    """Dialog for adding a new driver"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Add Driver"),
            rx.dialog.description(
                "Configure a new device driver for the platform driver agent"
            ),
            
            rx.vstack(
                # Driver type selection
                rx.vstack(
                    rx.text("Driver Type", size="2", weight="medium"),
                    rx.select(
                        ["fakedriver", "bacnet", "modbus", "dnp3"],
                        value=State._driver_type,
                        on_change=State.set_driver_type,
                        size="2",
                    ),
                    spacing="1",
                    width="100%",
                    align_items="start",
                ),
                
                # Location fields
                rx.text("Device Location", size="3", weight="bold", margin_top="1rem"),
                rx.grid(
                    rx.vstack(
                        rx.text("Campus", size="2", weight="medium"),
                        rx.input(
                            value=State._campus,
                            on_change=State.set_campus,
                            placeholder="campus",
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    rx.vstack(
                        rx.text("Building", size="2", weight="medium"),
                        rx.input(
                            value=State._building,
                            on_change=State.set_building,
                            placeholder="building",
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    rx.vstack(
                        rx.text("Unit", size="2", weight="medium"),
                        rx.input(
                            value=State._unit,
                            on_change=State.set_unit,
                            placeholder="device_name",
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    columns="3",
                    spacing="3",
                    width="100%",
                ),
                
                # Device path preview
                rx.callout.root(
                    rx.callout.icon(rx.icon("map-pin")),
                    rx.callout.text(
                        rx.text("Path: "),
                        rx.code(State.driver_path),
                    ),
                    size="1",
                    variant="soft",
                    width="100%",
                ),
                
                # Registry configuration
                rx.text("Registry Configuration", size="3", weight="bold", margin_top="1rem"),
                rx.cond(
                    State.available_registries,
                    rx.vstack(
                        rx.text("Select existing registry", size="2", weight="medium"),
                        rx.select(
                            State.available_registries_with_empty,
                            value=State._registry_config_name,
                            on_change=State.set_registry_config_name,
                            placeholder="Choose registry...",
                            size="2",
                        ),
                        rx.text("— or —", size="2", color="gray", align="center"),
                        spacing="2",
                        width="100%",
                        align_items="start",
                    ),
                ),
                rx.vstack(
                    rx.text("Upload new registry CSV", size="2", weight="medium"),
                    rx.input(
                        value=State._new_registry_name,
                        on_change=State.set_new_registry_name,
                        placeholder="registry_name.csv",
                        size="2",
                    ),
                    rx.text_area(
                        value=State._new_registry_content,
                        on_change=State.set_new_registry_content,
                        placeholder="Point Name,Volttron Point Name,Units,Writable,Type\nTemp1,Temperature1,F,FALSE,float",
                        size="2",
                        rows="4",
                    ),
                    spacing="2",
                    width="100%",
                    align_items="start",
                ),
                
                # Advanced settings (collapsed)
                rx.accordion.root(
                    rx.accordion.item(
                        header=rx.accordion.trigger(
                            "Advanced Settings",
                            rx.accordion.icon(),
                        ),
                        content=rx.accordion.content(
                            rx.vstack(
                                rx.grid(
                                    rx.vstack(
                                        rx.text("Scrape Interval (seconds)", size="2", weight="medium"),
                                        rx.input(
                                            value=str(State._interval),
                                            on_change=State.set_interval,
                                            type="number",
                                            size="2",
                                        ),
                                        spacing="1",
                                        width="100%",
                                        align_items="start",
                                    ),
                                    rx.vstack(
                                        rx.text("Timezone", size="2", weight="medium"),
                                        rx.input(
                                            value=State._timezone,
                                            on_change=State.set_timezone,
                                            size="2",
                                        ),
                                        spacing="1",
                                        width="100%",
                                        align_items="start",
                                    ),
                                    columns="2",
                                    spacing="3",
                                    width="100%",
                                ),
                                rx.vstack(
                                    rx.text("Heartbeat Point (optional)", size="2", weight="medium"),
                                    rx.input(
                                        value=State._heart_beat_point,
                                        on_change=State.set_heart_beat_point,
                                        placeholder="Heartbeat",
                                        size="2",
                                    ),
                                    spacing="1",
                                    width="100%",
                                    align_items="start",
                                ),
                                rx.vstack(
                                    rx.text("Driver Config JSON (optional)", size="2", weight="medium"),
                                    rx.text_area(
                                        value=State._driver_config_json,
                                        on_change=State.set_driver_config_json,
                                        placeholder='{"device_address": "192.168.1.100"}',
                                        size="2",
                                        rows="4",
                                    ),
                                    spacing="1",
                                    width="100%",
                                    align_items="start",
                                ),
                                spacing="3",
                                width="100%",
                            ),
                        ),
                    ),
                    collapsible=True,
                    variant="soft",
                    width="100%",
                ),
                
                spacing="3",
                width="100%",
            ),
            
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                    ),
                ),
                rx.dialog.close(
                    rx.button(
                        "Add Driver",
                        on_click=State.handle_add_driver,
                        disabled=~State.can_add_driver,
                    ),
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            
            max_width="700px",
            max_height="80vh",
            overflow_y="auto",
        ),
        open=State._show_add_driver_dialog,
    )


def edit_driver_dialog() -> rx.Component:
    """Dialog for editing an existing driver"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit Driver"),
            rx.dialog.description(
                "Modify driver configuration"
            ),
            
            rx.vstack(
                # Driver type selection
                rx.vstack(
                    rx.text("Driver Type", size="2", weight="medium"),
                    rx.select(
                        ["fakedriver", "bacnet", "modbus", "dnp3"],
                        value=State._driver_type,
                        on_change=State.set_driver_type,
                        size="2",
                    ),
                    spacing="1",
                    width="100%",
                    align_items="start",
                ),
                
                # Location fields
                rx.text("Device Location", size="3", weight="bold", margin_top="1rem"),
                rx.grid(
                    rx.vstack(
                        rx.text("Campus", size="2", weight="medium"),
                        rx.input(
                            value=State._campus,
                            on_change=State.set_campus,
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    rx.vstack(
                        rx.text("Building", size="2", weight="medium"),
                        rx.input(
                            value=State._building,
                            on_change=State.set_building,
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    rx.vstack(
                        rx.text("Unit", size="2", weight="medium"),
                        rx.input(
                            value=State._unit,
                            on_change=State.set_unit,
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    columns="3",
                    spacing="3",
                    width="100%",
                ),
                
                # Registry selection
                rx.vstack(
                    rx.text("Registry", size="2", weight="medium"),
                    rx.select(
                        State.available_registries,
                        value=State._registry_config_name,
                        on_change=State.set_registry_config_name,
                        size="2",
                    ),
                    spacing="1",
                    width="100%",
                    align_items="start",
                ),
                
                # Advanced settings
                rx.grid(
                    rx.vstack(
                        rx.text("Scrape Interval (seconds)", size="2", weight="medium"),
                        rx.input(
                            value=str(State._interval),
                            on_change=State.set_interval,
                            type="number",
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    rx.vstack(
                        rx.text("Timezone", size="2", weight="medium"),
                        rx.input(
                            value=State._timezone,
                            on_change=State.set_timezone,
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Heartbeat Point", size="2", weight="medium"),
                    rx.input(
                        value=State._heart_beat_point,
                        on_change=State.set_heart_beat_point,
                        size="2",
                    ),
                    spacing="1",
                    width="100%",
                    align_items="start",
                ),
                rx.vstack(
                    rx.text("Driver Config JSON", size="2", weight="medium"),
                    rx.text_area(
                        value=State._driver_config_json,
                        on_change=State.set_driver_config_json,
                        size="2",
                        rows="4",
                    ),
                    spacing="1",
                    width="100%",
                    align_items="start",
                ),
                
                spacing="3",
                width="100%",
            ),
            
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                    ),
                ),
                rx.dialog.close(
                    rx.button(
                        "Save Changes",
                        on_click=State.handle_edit_driver,
                        disabled=~State.can_add_driver,
                    ),
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            
            max_width="700px",
            max_height="80vh",
            overflow_y="auto",
        ),
        open=State._show_edit_driver_dialog,
    )


def delete_driver_dialog() -> rx.Component:
    """Dialog to confirm driver deletion"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Delete Driver"),
            rx.dialog.description(
                "Are you sure you want to delete this driver configuration?"
            ),
            
            rx.callout.root(
                rx.callout.icon(rx.icon("triangle-alert")),
                rx.callout.text(
                    "This will remove the driver configuration from the platform.driver agent. "
                    "The driver will stop collecting data after the agent is restarted."
                ),
                color_scheme="red",
                variant="soft",
                size="1",
            ),
            
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                    ),
                ),
                rx.dialog.close(
                    rx.button(
                        "Delete",
                        on_click=State.handle_delete_driver,
                        color_scheme="red",
                    ),
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            
            max_width="450px",
        ),
        open=State._show_delete_driver_dialog,
    )
