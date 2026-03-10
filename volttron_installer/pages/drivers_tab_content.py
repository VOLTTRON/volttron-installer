"""
Drivers Tab Content - UI for managing platform drivers
"""

import reflex as rx
from ..state import PlatformPageState as State


def _installed_driver_card(driver: dict) -> rx.Component:
    """Card for a single installed driver library."""
    return rx.card(
        rx.hstack(
            rx.center(
                rx.icon("package-check", size=18, color="var(--green-9)"),
                width="30px",
                height="30px",
                border_radius="8px",
                background="var(--green-3)",
            ),
            rx.vstack(
                rx.text(driver["name"], weight="bold", size="3"),
                rx.text(f"Version {driver['version']}", size="1", color="gray"),
                spacing="1",
                align_items="start",
                flex="1",
            ),
            rx.button(
                rx.icon("settings", size=14),
                "Configure",
                size="1",
                variant="soft",
                on_click=State.open_configure_driver_dialog(driver["name"]),
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        width="100%",
        variant="surface",
        _hover={"background": "var(--gray-2)"},
    )


def _summary_stat(label: str, value: rx.Var | str, icon: str) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.center(
                rx.icon(icon, size=18, color="var(--accent-10)"),
                width="34px",
                height="34px",
                border_radius="9px",
                background="var(--accent-3)",
            ),
            rx.vstack(
                rx.text(label, size="1", color="gray", weight="medium"),
                rx.text(value, size="5", weight="bold"),
                spacing="0",
                align_items="start",
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
            rx.vstack(
                rx.text("Installed Driver Libraries", size="4", weight="bold"),
                rx.text(
                    "Libraries available in this platform's virtual environment.",
                    size="1",
                    color="gray",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=14),
                "Refresh",
                on_click=State.fetch_installed_driver_libs,
                size="1",
                variant="ghost",
                color_scheme="gray",
                loading=State.loading_installed_drivers,
            ),
            spacing="3",
            align="center",
            width="100%",
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
                rx.box(
                    rx.vstack(
                    rx.foreach(
                        State.installed_driver_libs,
                        _installed_driver_card,
                    ),
                        spacing="2",
                        width="100%",
                    ),
                    max_height="320px",
                    overflow_y="auto",
                    width="100%",
                ),
                rx.callout(
                    rx.text(
                        "No driver libraries installed yet. Use Install Driver Library to add your first driver package.",
                        size="2",
                    ),
                    icon="info",
                    color_scheme="gray",
                ),
            ),
        ),
        spacing="3",
        width="100%",
    )


def _tree_row(row: dict) -> rx.Component:
    """Render one row of the config store tree — either an agent header or a key entry."""
    return rx.cond(
        row["type"] == "agent",
        # ── Agent header row ──────────────────────────────────────────────
        rx.hstack(
            rx.cond(
                row["expanded"],
                rx.icon("chevron-down", size=15, color="gray"),
                rx.icon("chevron-right", size=15, color="gray"),
            ),
            rx.icon("layers", size=15, color="#60a5fa"),
            rx.text(
                row["agent"],
                size="2",
                weight="medium",
                font_family="monospace",
                flex="1",
            ),
            rx.cond(
                row["loading"],
                rx.spinner(size="1"),
                rx.fragment(),
            ),
            on_click=State.toggle_agent_tree(row["agent"]),
            style={"cursor": "pointer"},
            spacing="2",
            align="center",
            padding_y="5px",
            padding_x="4px",
            border_radius="4px",
            _hover={"background": "var(--gray-3)"},
            width="100%",
        ),
        # ── Config key row ────────────────────────────────────────────────
        rx.hstack(
            rx.hstack(
                rx.icon("file-text", size=14, color="gray"),
                rx.text(
                    row["key"],
                    size="2",
                    font_family="monospace",
                    flex="1",
                    no_of_lines=1,
                ),
                spacing="2",
                align="center",
                flex="1",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("pencil", size=14),
                    rx.text(
                        "Edit",
                        class_name="cfg-action-label",
                        style={"@media (max-width: 1280px)": {"display": "none"}},
                    ),
                    size="1",
                    variant="soft",
                    color_scheme="gray",
                    loading=State.live_key_loading & (State.live_editing_key == row["key"]),
                    on_click=State.open_edit_live_config_key(row["agent"], row["key"]),
                    min_width="52px",
                    title="Edit key",
                ),
                rx.button(
                    rx.icon("trash-2", size=14),
                    rx.text(
                        "Delete",
                        class_name="cfg-action-label",
                        style={"@media (max-width: 1280px)": {"display": "none"}},
                    ),
                    size="1",
                    variant="soft",
                    color_scheme="red",
                    on_click=State.open_delete_live_config_dialog(row["agent"], row["key"]),
                    min_width="52px",
                    title="Delete key",
                ),
                spacing="2",
                align="center",
                flex_shrink="0",
            ),
            spacing="2",
            align="center",
            padding_left="2rem",
            padding_y="8px",
            padding_right="0.5rem",
            border_radius="6px",
            _hover={"background": "var(--gray-2)"},
            width="100%",
        ),
    )


def platform_driver_config_section() -> rx.Component:
    """Section showing live vctl config store as a dynamic, flicker-free tree."""
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("Live Config Store", size="4", weight="bold"),
                rx.text(
                    "Driver config keys currently loaded in the running platform (edit or delete from here).",
                    size="1",
                    color="gray",
                ),
                rx.text(
                    "Tip: On smaller screens, action labels collapse to icons to keep rows readable.",
                    size="1",
                    color="gray",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.cond(
                State.vctl_agents_loading,
                rx.hstack(
                    rx.spinner(size="1"),
                    rx.text("Refreshing…", size="1", color="gray"),
                    spacing="1",
                    align="center",
                ),
                rx.button(
                    rx.icon("refresh-cw", size=13),
                    "Refresh",
                    on_click=State.fetch_vctl_config_list,
                    size="1",
                    variant="ghost",
                    color_scheme="gray",
                ),
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        rx.cond(
            State.vctl_config_agents.length() > 0,
            rx.box(
                rx.foreach(State.config_tree_rows, _tree_row),
                width="100%",
                min_height="320px",
                max_height="420px",
                overflow_y="auto",
                border="1px solid var(--gray-5)",
                border_radius="10px",
                padding="0.5rem",
                background="var(--gray-1)",
            ),
            rx.cond(
                State.vctl_agents_loading,
                rx.fragment(),
                rx.callout(
                    rx.text(
                        "No agents found in config store yet. Click Refresh to scan active config entries.",
                        size="2",
                    ),
                    icon="search",
                    color_scheme="gray",
                ),
            ),
        ),
        spacing="2",
        width="100%",
    )


def drivers_tab_content() -> rx.Component:
    """Main drivers tab content with clearer IA and better space usage."""
    return rx.vstack(
        # Header + primary actions
        rx.hstack(
            rx.vstack(
                rx.heading("Drivers Workspace", size="6"),
                rx.text(
                    "Manage driver libraries and live config keys from one place.",
                    size="2",
                    color="gray",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("refresh-cw", size=14),
                    "Refresh All",
                    on_click=[State.fetch_installed_driver_libs, State.fetch_vctl_config_list],
                    size="2",
                    variant="soft",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.icon("package-plus"),
                    "Install Driver Library",
                    on_click=State.open_install_driver_lib_dialog,
                    size="2",
                    variant="solid",
                    color_scheme="purple",
                ),
                spacing="2",
                align="center",
            ),
            align="end",
            justify="between",
            width="100%",
            spacing="4",
        ),

        # Snapshot stats
        rx.grid(
            _summary_stat("Installed Libraries", State.installed_driver_libs.length(), "package-check"),
            _summary_stat("Config Agents", State.vctl_config_agents.length(), "layers"),
            _summary_stat("Config Entries", State.config_tree_rows.length(), "file-text"),
            columns="3",
            spacing="3",
            width="100%",
        ),

        # Main workspace
        rx.grid(
            rx.card(
                installed_driver_libs_section(),
                width="100%",
                height="100%",
                padding="1rem",
            ),
            rx.card(
                platform_driver_config_section(),
                width="100%",
                height="100%",
                padding="1rem",
            ),
            columns="2",
            spacing="3",
            width="100%",
        ),

        # Dialogs
        add_driver_dialog(),
        edit_driver_dialog(),
        delete_driver_dialog(),
        install_driver_lib_dialog(),
        configure_driver_dialog(),
        delete_live_config_dialog(),
        live_config_edit_dialog(),

        spacing="4",
        width="100%",
        padding="1.25rem",
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


def _configure_field_input(field: dict) -> rx.Component:
    """Render a driver_config field editor based on the field metadata type."""
    field_key = field.get("key", "")
    field_type = field.get("type", "text")

    return rx.match(
        field_type,
        (
            "checkbox",
            rx.checkbox(
                checked=rx.cond(field.get("value", False), True, False),
                on_change=lambda checked: State.toggle_configure_driver_field(field_key, checked),
            ),
        ),
        (
            "password",
            rx.input(
                type="password",
                value=field.get("value", ""),
                on_change=lambda value: State.set_configure_driver_field(field_key, value),
                size="2",
                width="100%",
                font_family="monospace",
            ),
        ),
        (
            "number",
            rx.input(
                type="number",
                value=field.get("value", ""),
                on_change=lambda value: State.set_configure_driver_field(field_key, value),
                size="2",
                width="100%",
                font_family="monospace",
            ),
        ),
        (
            "float",
            rx.input(
                type="number",
                step="any",
                value=field.get("value", ""),
                on_change=lambda value: State.set_configure_driver_field(field_key, value),
                size="2",
                width="100%",
                font_family="monospace",
            ),
        ),
        rx.input(
            value=field.get("value", ""),
            on_change=lambda value: State.set_configure_driver_field(field_key, value),
            size="2",
            width="100%",
            font_family="monospace",
        ),
    )


def _configure_field_row(field: dict) -> rx.Component:
    """Single row for a structured driver_config field."""
    return rx.vstack(
        rx.hstack(
            rx.text(field.get("label", field.get("key", "")), size="2", weight="medium"),
            rx.cond(field.get("required", False), rx.badge("Required", size="1", color_scheme="amber"), rx.fragment()),
            spacing="2",
            align="center",
            width="100%",
        ),
        _configure_field_input(field),
        rx.cond(
            field.get("description", "") != "",
            rx.text(field.get("description", ""), size="1", color="gray"),
            rx.fragment(),
        ),
        spacing="1",
        align_items="start",
        width="100%",
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
                rx.hstack(
                    rx.button(
                        "From Catalog",
                        on_click=lambda: State.set_install_driver_lib_mode("catalog"),
                        variant=rx.cond(State.install_driver_lib_mode == "catalog", "solid", "soft"),
                        color_scheme=rx.cond(State.install_driver_lib_mode == "catalog", "blue", "gray"),
                        size="2",
                    ),
                    rx.button(
                        "Local Libraries",
                        on_click=lambda: State.set_install_driver_lib_mode("local"),
                        variant=rx.cond(State.install_driver_lib_mode == "local", "solid", "soft"),
                        color_scheme=rx.cond(State.install_driver_lib_mode == "local", "blue", "gray"),
                        size="2",
                    ),
                    rx.button(
                        "Manual",
                        on_click=lambda: State.set_install_driver_lib_mode("manual"),
                        variant=rx.cond(State.install_driver_lib_mode == "manual", "solid", "soft"),
                        color_scheme=rx.cond(State.install_driver_lib_mode == "manual", "blue", "gray"),
                        size="2",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.divider(),

                rx.cond(
                    State.install_driver_lib_mode == "catalog",
                    rx.vstack(
                        rx.text("Available Drivers", size="3", weight="bold"),
                        rx.vstack(
                            rx.foreach(
                                State.driver_library_catalog,
                                _driver_lib_card,
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.cond(
                        State.install_driver_lib_mode == "local",
                        rx.vstack(
                            rx.callout.root(
                                rx.callout.icon(rx.icon("info")),
                                rx.callout.text(
                                    "Driver repos found in ~/volttron-workspace (must include pyproject.toml). "
                                    "Install uses the local path on this machine.",
                                ),
                                size="1",
                                variant="soft",
                                width="100%",
                            ),
                            rx.cond(
                                State.loading_local_driver_libs,
                                rx.center(
                                    rx.hstack(
                                        rx.spinner(size="2"),
                                        rx.text("Scanning local workspace…", size="2", color="gray"),
                                        spacing="2",
                                        align="center",
                                    ),
                                    padding="1rem",
                                    width="100%",
                                ),
                                rx.cond(
                                    State.has_local_driver_libs,
                                    rx.box(
                                        rx.vstack(
                                            rx.foreach(
                                                State.local_driver_libs,
                                                lambda lib: rx.box(
                                                    rx.card(
                                                        rx.flex(
                                                            rx.vstack(
                                                                rx.text(lib["name"], weight="bold", size="3"),
                                                                rx.text(lib["path"], size="1", color="gray", font_family="monospace"),
                                                                rx.cond(
                                                                    lib["description"] != "",
                                                                    rx.text(lib["description"], size="2", color="gray"),
                                                                ),
                                                                spacing="1",
                                                                align_items="start",
                                                                flex="1",
                                                            ),
                                                            rx.cond(
                                                                State.selected_local_driver_lib == lib["path"],
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
                                                            State.selected_local_driver_lib == lib["path"],
                                                            "surface",
                                                            "ghost",
                                                        ),
                                                    ),
                                                    on_click=State.select_local_driver_lib(lib["path"]),
                                                    width="100%",
                                                    style={"cursor": "pointer"},
                                                ),
                                            ),
                                            spacing="2",
                                            width="100%",
                                        ),
                                        width="100%",
                                        max_height="300px",
                                        overflow_y="auto",
                                        padding="0.5rem",
                                    ),
                                    rx.callout.root(
                                        rx.callout.icon(rx.icon("folder-open")),
                                        rx.callout.text(
                                            "No local driver libraries found. Add driver repos under ~/volttron-workspace.",
                                        ),
                                        color="gray",
                                        variant="soft",
                                        width="100%",
                                    ),
                                ),
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.text("Manual Source", size="3", weight="bold"),
                            rx.input(
                                value=State.custom_driver_lib,
                                on_change=State.set_custom_driver_lib,
                                placeholder="volttron-lib-my-driver, git+https://..., or /path/to/local/repo",
                                size="2",
                                width="100%",
                            ),
                            rx.text(
                                "Supports PyPI package names, Git URLs, and local filesystem paths.",
                                size="1",
                                color="gray",
                            ),
                            spacing="2",
                            width="100%",
                        ),
                    ),
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
                    disabled=~State.can_install_driver_lib,
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
    """Two-step wizard: step 1 = device JSON editor, step 2 = registry CSV editor."""
    return rx.dialog.root(
        rx.dialog.content(
            # ── Step 1: Device config JSON ──────────────────────────────────
            rx.cond(
                State.configure_step == 1,
                rx.vstack(
                    rx.hstack(
                        rx.icon("settings", size=18),
                        rx.dialog.title(
                            f"Configure {State.configure_driver_name} — Step 1 of 2: Device Config",
                            size="4",
                        ),
                        align="center",
                        spacing="2",
                    ),
                    rx.dialog.description(
                        "Set the config key name (e.g. devices/campus/building/fake) and edit the JSON below.",
                        size="2",
                    ),
                    rx.cond(
                        State.configure_required_agents.length() > 0,
                        rx.callout.root(
                            rx.callout.icon(rx.icon("info")),
                            rx.callout.text(
                                "Required supporting agent(s): ",
                                rx.foreach(
                                    State.configure_required_agents,
                                    lambda identity: rx.code(identity, size="1"),
                                ),
                            ),
                            color_scheme="amber",
                            size="1",
                            variant="soft",
                            width="100%",
                        ),
                    ),
                    rx.vstack(
                        rx.text("Config Key Name", size="2", weight="medium"),
                        rx.input(
                            value=State.configure_device_name,
                            on_change=State.set_configure_device_name,
                            placeholder="devices/campus/building/fake",
                            size="2",
                            width="100%",
                            font_family="monospace",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    rx.cond(
                        State.configure_has_field_form,
                        rx.card(
                            rx.vstack(
                                rx.text("Driver Config", size="3", weight="bold"),
                                rx.foreach(
                                    State.configure_driver_fields_with_values,
                                    _configure_field_row,
                                ),
                                spacing="3",
                                width="100%",
                                align_items="start",
                            ),
                            width="100%",
                            variant="surface",
                        ),
                    ),
                    rx.text("Device JSON", size="2", weight="medium"),
                    rx.text_area(
                        value=State.configure_device_json,
                        on_change=State.set_configure_device_json,
                        rows="22",
                        font_family="monospace",
                        font_size="12px",
                        width="100%",
                        resize="vertical",
                        margin_top="0.25rem",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button(
                                "Cancel",
                                variant="soft",
                                color_scheme="gray",
                                on_click=State.close_configure_driver_dialog,
                            ),
                        ),
                        rx.button(
                            "Next →",
                            on_click=State.configure_next_step,
                            color_scheme="blue",
                            disabled=State.configure_device_name == "",
                        ),
                        spacing="3",
                        margin_top="1rem",
                        justify="end",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
            # ── Step 2: Registry CSV editor ─────────────────────────────────
            rx.cond(
                State.configure_step == 2,
                rx.vstack(
                    rx.hstack(
                        rx.icon("table", size=18),
                        rx.dialog.title(
                            f"Configure {State.configure_driver_name} — Step 2 of 2: Registry CSV",
                            size="4",
                        ),
                        align="center",
                        spacing="2",
                    ),
                    rx.dialog.description(
                        "Set the CSV key name (e.g. fake.csv) and edit the registry contents below.",
                        size="2",
                    ),
                    rx.vstack(
                        rx.text("CSV Key Name", size="2", weight="medium"),
                        rx.input(
                            value=State.configure_csv_name,
                            on_change=State.set_configure_csv_name,
                            placeholder="fake.csv",
                            size="2",
                            width="100%",
                            font_family="monospace",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="start",
                    ),
                    rx.text_area(
                        value=State.configure_csv_content,
                        on_change=State.set_configure_csv_content,
                        rows="22",
                        font_family="monospace",
                        font_size="12px",
                        width="100%",
                        resize="vertical",
                        margin_top="0.25rem",
                    ),
                    rx.flex(
                        rx.button(
                            "← Back",
                            on_click=State.configure_prev_step,
                            variant="soft",
                            color_scheme="gray",
                        ),
                        rx.button(
                            rx.cond(
                                State.deploying_configs,
                                rx.hstack(rx.spinner(size="1"), rx.text("Saving…"), spacing="2", align="center"),
                                rx.text("Save & Deploy"),
                            ),
                            on_click=State.handle_configure_driver_save,
                            disabled=State.configure_csv_name == "" | State.deploying_configs,
                            color_scheme="blue",
                        ),
                        spacing="3",
                        margin_top="1rem",
                        justify="end",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
            max_width="800px",
            width="90vw",
        ),
        open=State.show_configure_driver_dialog,
        on_open_change=State.close_configure_driver_dialog,
    )
