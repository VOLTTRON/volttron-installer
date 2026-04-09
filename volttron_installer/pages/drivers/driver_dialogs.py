"""Driver CRUD dialogs — add, edit, delete driver and live config key dialogs."""

import reflex as rx
from ...state import PlatformPageState as State


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
                        State.driver_type_options,
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
                        State.driver_type_options,
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


def delete_live_config_dialog() -> rx.Component:
    """Confirm-delete dialog for a live vctl config key."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Delete Config Entry"),
            rx.dialog.description(
                rx.hstack(
                    rx.code(State.live_editing_agent, size="1"),
                    rx.text("→", size="2", color="gray"),
                    rx.code(State.live_editing_key, size="1"),
                    spacing="2",
                    align="center",
                ),
            ),
            rx.callout.root(
                rx.callout.icon(rx.icon("triangle-alert")),
                rx.callout.text(
                    "This will permanently remove the entry via ",
                    rx.text.strong("vctl config delete"),
                    ".",
                ),
                color_scheme="red",
                variant="soft",
                size="1",
                margin_top="0.5rem",
            ),
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=State.close_delete_live_config_dialog,
                    ),
                ),
                rx.dialog.close(
                    rx.button(
                        "Delete",
                        on_click=State.confirm_delete_live_config_key,
                        color_scheme="red",
                    ),
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            max_width="450px",
        ),
        open=State.show_delete_live_config_dialog,
        on_open_change=State.close_delete_live_config_dialog,
    )


def live_config_edit_dialog() -> rx.Component:
    """Simple raw-text editor for any live vctl config entry."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("file-pen"),
                    rx.code(State.live_editing_agent, size="2"),
                    rx.text("→", size="2", color="gray"),
                    rx.code(State.live_editing_key, size="2"),
                    align="center",
                    spacing="2",
                ),
            ),
            rx.text_area(
                value=State.live_edit_content,
                on_change=State.set_live_edit_content,
                rows="22",
                font_family="monospace",
                font_size="12px",
                width="100%",
                margin_top="0.75rem",
                resize="vertical",
            ),
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=State.close_live_edit_dialog,
                    ),
                ),
                rx.button(
                    rx.cond(
                        State.live_edit_saving,
                        rx.hstack(rx.spinner(size="1"), rx.text("Saving…"), spacing="2", align="center"),
                        rx.text("Save"),
                    ),
                    on_click=State.save_live_edit_content,
                    disabled=State.live_edit_saving,
                    color_scheme="blue",
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            max_width="800px",
            width="90vw",
        ),
        open=State.show_live_edit_dialog,
        on_open_change=State.close_live_edit_dialog,
    )