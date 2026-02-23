"""
Drivers Tab Content - UI for managing platform drivers
"""

import reflex as rx
from ..state import PlatformPageState as State


def _installed_driver_card(driver: dict) -> rx.Component:
    """Card for a single installed driver library."""
    return rx.card(
        rx.hstack(
            rx.icon("package-check", size=20, color="green"),
            rx.vstack(
                rx.text(driver["name"], weight="bold", size="3"),
                rx.text(driver["version"], size="1", color="gray"),
                spacing="1",
                align_items="start",
                flex="1",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        width="100%",
        variant="surface",
    )


def installed_driver_libs_section() -> rx.Component:
    """Section showing installed driver libraries."""
    return rx.vstack(
        rx.hstack(
            rx.text("Installed Driver Libraries", size="4", weight="bold"),
            rx.button(
                rx.icon("refresh-cw", size=14),
                "Refresh",
                on_click=State.fetch_installed_driver_libs,
                size="1",
                variant="ghost",
                color_scheme="gray",
                loading=State.loading_installed_drivers,
            ),
            spacing="2",
            align="center",
        ),
        rx.cond(
            State.loading_installed_drivers,
            rx.center(
                rx.hstack(
                    rx.spinner(size="2"),
                    rx.text("Scanning venv…", size="2", color="gray"),
                    spacing="2",
                    align="center",
                ),
                padding="1rem",
                width="100%",
            ),
            rx.cond(
                State.installed_driver_libs.length() > 0,
                rx.vstack(
                    rx.foreach(
                        State.installed_driver_libs,
                        _installed_driver_card,
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.text(
                    "No driver libraries installed yet. Use 'Install Driver Library' to add one.",
                    size="2",
                    color="gray",
                ),
            ),
        ),
        spacing="3",
        width="100%",
    )


def _config_key_row(key: str) -> rx.Component:
    """A single config key row in the platform.driver tree."""
    return rx.hstack(
        rx.icon("file-text", size=14, color="gray"),
        rx.text(key, size="2", font_family="monospace"),
        spacing="2",
        align="center",
        padding_left="1.5rem",
        padding_y="2px",
        width="100%",
    )


def platform_driver_config_section() -> rx.Component:
    """Section showing live vctl config list output as a simple tree."""
    return rx.vstack(
        rx.hstack(
            rx.text("Config Store (live)", size="4", weight="bold"),
            rx.button(
                rx.icon("refresh-cw", size=14),
                "Refresh",
                on_click=State.fetch_vctl_config_list,
                size="1",
                variant="ghost",
                color_scheme="gray",
                loading=State.vctl_config_loading,
            ),
            spacing="2",
            align="center",
        ),
        rx.cond(
            State.vctl_config_loading,
            rx.center(
                rx.hstack(
                    rx.spinner(size="2"),
                    rx.text("Running vctl config list…", size="2", color="gray"),
                    spacing="2",
                    align="center",
                ),
                padding="1rem",
                width="100%",
            ),
            rx.cond(
                State.platform_driver_in_config_store,
                # platform.driver is present — show tree row
                rx.vstack(
                    rx.box(
                        rx.hstack(
                            rx.cond(
                                State.platform_driver_tree_expanded,
                                rx.icon("chevron-down", size=16),
                                rx.icon("chevron-right", size=16),
                            ),
                            rx.icon("layers", size=16, color="blue"),
                            rx.text("platform.driver", size="2", weight="medium", font_family="monospace"),
                            spacing="2",
                            align="center",
                        ),
                        on_click=State.toggle_platform_driver_tree,
                        style={"cursor": "pointer"},
                        padding_y="4px",
                        width="100%",
                    ),
                    rx.cond(
                        State.platform_driver_tree_expanded,
                        rx.cond(
                            State.vctl_config_keys.length() > 0,
                            rx.vstack(
                                rx.foreach(State.vctl_config_keys, _config_key_row),
                                spacing="0",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.text("No configs found", size="2", color="gray"),
                                rx.button(
                                    rx.icon("plus", size=14),
                                    "Add Config",
                                    on_click=State.open_add_driver_dialog,
                                    size="1",
                                    variant="soft",
                                ),
                                spacing="3",
                                align="center",
                                padding_left="1.5rem",
                            ),
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
                # platform.driver not yet in config store
                rx.text(
                    "platform.driver not found in config store",
                    size="2",
                    color="gray",
                ),
            ),
        ),
        spacing="2",
        width="100%",
    )


def drivers_tab_content() -> rx.Component:
    """Main drivers tab content with driver list and management controls"""
    return rx.vstack(
        # Header with add button
        rx.hstack(
            rx.heading("Platform Drivers", size="6"),
            rx.button(
                rx.icon("package-plus"),
                "Install Driver Library",
                on_click=State.open_install_driver_lib_dialog,
                size="2",
                variant="soft",
                color_scheme="purple",
            ),
            justify="between",
            width="100%",
            align="center",
        ),

        # Installed driver libraries section
        installed_driver_libs_section(),

        rx.divider(),

        # Live config store section
        platform_driver_config_section(),

        # Dialogs
        add_driver_dialog(),
        edit_driver_dialog(),
        delete_driver_dialog(),
        install_driver_lib_dialog(),
        configure_driver_dialog(),

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
                        ["fake", "bacnet", "modbus", "dnp3", "homeassistant"],
                        value=State.driver_type,
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
                            value=State.campus,
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
                            value=State.building,
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
                            value=State.unit,
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
                            value=State.registry_config_name,
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
                        value=State.new_registry_name,
                        on_change=State.set_new_registry_name,
                        placeholder="registry_name.csv",
                        size="2",
                    ),
                    rx.text_area(
                        value=State.new_registry_content,
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
                                            value=str(State.interval),
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
                                            value=State.timezone,
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
                                        value=State.heart_beat_point,
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
                                        value=State.driver_config_json,
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
        open=State.show_add_driver_dialog,
        on_open_change=State.close_add_driver_dialog,
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
                        ["fake", "bacnet", "modbus", "dnp3", "homeassistant"],
                        value=State.driver_type,
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
                            value=State.campus,
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
                            value=State.building,
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
                            value=State.unit,
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
                        value=State.registry_config_name,
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
                            value=str(State.interval),
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
                            value=State.timezone,
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
                        value=State.heart_beat_point,
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
                        value=State.driver_config_json,
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
        open=State.show_edit_driver_dialog,
        on_open_change=State.close_edit_driver_dialog,
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
        open=State.show_delete_driver_dialog,
        on_open_change=State.close_delete_driver_dialog,
    )


def _driver_lib_card(driver: dict) -> rx.Component:
    """Render a single driver library option as a selectable card."""
    return rx.box(
        rx.card(
            rx.flex(
                rx.vstack(
                    rx.text(driver["name"], weight="bold", size="3"),
                    rx.text(driver["description"], size="2", color="gray"),
                    rx.code(driver["pip_package"], size="1"),
                    spacing="1",
                    align_items="start",
                    flex="1",
                ),
                rx.cond(
                    State.selected_driver_lib == driver["pip_package"],
                    rx.icon("check", size=20, color="green"),
                    rx.box(width="20px", height="20px"),
                ),
                justify="between",
                align="center",
                width="100%",
                gap="3",
            ),
            width="100%",
            variant=rx.cond(
                State.selected_driver_lib == driver["pip_package"],
                "surface",
                "ghost",
            ),
        ),
        on_click=State.set_selected_driver_lib(driver["pip_package"]),
        width="100%",
        style={"cursor": "pointer"},
    )


def install_driver_lib_dialog() -> rx.Component:
    """Dialog for installing a driver library into the VOLTTRON venv."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Install Driver Library"),
            rx.dialog.description(
                "Install a driver library into the VOLTTRON virtual environment. "
                "This is required before adding driver configurations of that type."
            ),

            rx.vstack(
                # Catalog list
                rx.text("Available Drivers", size="3", weight="bold"),
                rx.vstack(
                    rx.foreach(
                        State.driver_library_catalog,
                        _driver_lib_card,
                    ),
                    spacing="2",
                    width="100%",
                ),

                # Custom package input
                rx.separator(),
                rx.text("Custom Driver Package", size="3", weight="bold"),
                rx.text(
                    "Enter a pip package name for a driver not listed above.",
                    size="2",
                    color="gray",
                ),
                rx.input(
                    value=State.custom_driver_lib,
                    on_change=State.set_custom_driver_lib,
                    placeholder="volttron-lib-my-custom-driver",
                    size="2",
                ),

                # Install result feedback
                rx.cond(
                    State.driver_lib_install_result != "",
                    rx.callout.root(
                        rx.callout.text(State.driver_lib_install_result),
                        size="1",
                        variant="soft",
                        width="100%",
                    ),
                ),

                spacing="3",
                width="100%",
                padding_top="0.5rem",
            ),

            rx.flex(
                rx.button(
                    "Close",
                    on_click=State.close_install_driver_lib_dialog,
                    variant="soft",
                    color_scheme="gray",
                ),
                rx.button(
                    "Install",
                    on_click=State.handle_install_driver_lib,
                    loading=State.installing_driver_lib,
                    disabled=State.driver_lib_to_install == "",
                    color_scheme="purple",
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),

            max_width="550px",
        ),
        open=State.show_install_driver_lib_dialog,
        on_open_change=State.close_install_driver_lib_dialog,
    )


def configure_driver_dialog() -> rx.Component:
    """Dialog for configuring a driver with pre-filled templates."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title(
                    rx.hstack(
                        rx.icon("settings", size=20),
                        rx.text(f"Configure {State.configure_driver_name}"),
                        spacing="2",
                        align="center",
                    ),
                ),
                rx.dialog.description(
                    "Edit the device config and registry CSV below, then save. "
                    "You can modify the templates or replace them entirely.",
                    size="2",
                ),

                # Location fields
                rx.text("Device Location", size="3", weight="bold"),
                rx.grid(
                    rx.vstack(
                        rx.text("Campus", size="2", weight="medium"),
                        rx.input(
                            value=State.campus,
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
                            value=State.building,
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
                            value=State.unit,
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

                # Path preview
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

                # Scrape settings
                rx.grid(
                    rx.vstack(
                        rx.text("Interval (s)", size="2", weight="medium"),
                        rx.input(
                            value=str(State.interval),
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
                            value=State.timezone,
                            on_change=State.set_timezone,
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    rx.vstack(
                        rx.text("Heartbeat Point", size="2", weight="medium"),
                        rx.input(
                            value=State.heart_beat_point,
                            on_change=State.set_heart_beat_point,
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

                rx.separator(),

                # Device Config JSON
                rx.vstack(
                    rx.text("Device Config JSON", size="3", weight="bold"),
                    rx.text(
                        "Protocol-specific settings (e.g. device address, port).",
                        size="2",
                        color="gray",
                    ),
                    rx.text_area(
                        value=State.driver_config_json,
                        on_change=State.set_driver_config_json,
                        placeholder='{"device_address": "10.0.0.1"}',
                        size="2",
                        rows="5",
                        font_family="monospace",
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                    align_items="start",
                ),

                rx.separator(),

                # Registry CSV
                rx.vstack(
                    rx.text("Registry CSV", size="3", weight="bold"),
                    rx.text(
                        "Defines the data points to scrape from the device.",
                        size="2",
                        color="gray",
                    ),
                    rx.vstack(
                        rx.text("Registry Name", size="2", weight="medium"),
                        rx.input(
                            value=State.new_registry_name,
                            on_change=State.set_new_registry_name,
                            placeholder="fake_registry.csv",
                            size="2",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    rx.text_area(
                        value=State.new_registry_content,
                        on_change=State.set_new_registry_content,
                        placeholder="Point Name,Volttron Point Name,Units,Writable,Type",
                        size="2",
                        rows="8",
                        font_family="monospace",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                    align_items="start",
                ),

                spacing="4",
                width="100%",
            ),

            rx.flex(
                rx.button(
                    "Cancel",
                    on_click=State.close_configure_driver_dialog,
                    variant="soft",
                    color_scheme="gray",
                ),
                rx.button(
                    "Save Driver Config",
                    on_click=State.handle_configure_driver_save,
                    disabled=~State.can_add_driver,
                    color_scheme="blue",
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),

            max_width="700px",
            max_height="85vh",
            overflow_y="auto",
        ),
        open=State.show_configure_driver_dialog,
        on_open_change=State.close_configure_driver_dialog,
    )
