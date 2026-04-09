"""Driver library installation and driver configuration dialogs."""

import reflex as rx
from ...state import PlatformPageState as State


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