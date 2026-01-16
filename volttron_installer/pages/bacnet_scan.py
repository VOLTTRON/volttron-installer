import reflex as rx
from ..state import BacnetScanState, ToolState, PlatformPageState
from ..components.form_components import form_entry
from ..components.tiles import platform_tile
from ..components.buttons.tile_icon import tile_icon
from ..layouts import app_layout_sidebar
from ..model_views import BACnetDeviceModelView, BACnetDevicePointModelView

def filter_badge(text: str, cursor: str = "pointer", **props) -> rx.Component:
    return rx.badge(
        rx.hstack(
            rx.icon("x", size=12),
            rx.text(text),
            spacing="1",
            align="center"
        ),
        color_scheme="blue",
        variant="surface",
        cursor=cursor,
        size="1",
        **props
    )

def table_filter_trigger() -> rx.Component:
    return tile_icon(
        "search",
    )

def volttron_point_name_filter_popover() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            table_filter_trigger()
        ),
        rx.popover.content(
            rx.form(
                rx.vstack(
                    form_entry.form_entry(
                        "VOLTTRON Point Name Filter",
                        rx.input(
                            width="100%",
                            placeholder="Filter for a value",
                            name="volttron_point_name",
                            default_value=BacnetScanState.point_table_filter.volttron_point_name,
                        )
                    ),
                    rx.popover.close(
                        rx.button(
                            "Save",
                            width="100%",
                            type="submit"
                        )
                    )
                ),
                on_submit = BacnetScanState.filter_form_submit
            )
        ),
    )

def units_filter_popover() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            table_filter_trigger()
        ),
        rx.popover.content(
            rx.form(
                rx.vstack(
                    form_entry.form_entry(
                        "Units Filter",
                        rx.input(
                            width="100%",
                            placeholder="Filter for a value",
                            name="units",
                            default_value=BacnetScanState.point_table_filter.units,
                        )
                    ),
                    rx.popover.close(
                        rx.button(
                            "Save",
                            width="100%",
                            type="submit"
                        )
                    )
                ),
                on_submit = BacnetScanState.filter_form_submit
            )
        ),
    )

def object_type_filter_popover() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            table_filter_trigger()
        ),
        rx.popover.content(
            rx.form(
                rx.vstack(
                    form_entry.form_entry(
                        "BACnet Object Type Filter",
                        rx.input(
                            placeholder="Filter for a value",
                            name="object_type",
                            default_value=BacnetScanState.point_table_filter.object_type,
                            width="100%"
                        )
                    ),
                    rx.popover.close(
                        rx.button(
                            "Save",
                            width="100%",
                            type="submit"
                        )
                    )
                ),
                on_submit = BacnetScanState.filter_form_submit
            )
        ),
    )

def present_value_filter_popover() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            table_filter_trigger()
        ),
        rx.popover.content(
            rx.form(
                rx.vstack(
                    form_entry.form_entry(
                        "Present Value Filter",
                        rx.input(
                            placeholder="Filter for a value",
                            name="present_value",
                            default_value=BacnetScanState.point_table_filter.present_value,
                            width="100%"
                        )
                    ),
                    rx.popover.close(
                        rx.button(
                            "Save",
                            width="100%",
                            type="submit"
                        )
                    )
                ),
                on_submit = BacnetScanState.filter_form_submit
            )
        ),
    )
 
def writable_filter_popover() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            table_filter_trigger()
        ),
        rx.popover.content(
            rx.form(
                rx.vstack(
                    form_entry.form_entry(
                        "Writable Filter",
                        rx.select(
                            [" ", "TRUE", "FALSE"],
                            name="writable",
                            default_value=BacnetScanState.point_table_filter.writable,
                            width="100%"
                        )
                    ),
                    rx.popover.close(
                        rx.button(
                            "Save",
                            width="100%",
                            type="submit"
                        )
                    )
                ),
                on_submit = BacnetScanState.filter_form_submit
            )
        ),
    )

def index_filter_popover() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            table_filter_trigger()
        ),
        rx.popover.content(
            rx.form(
                rx.vstack(
                    form_entry.form_entry(
                        "Index Filter",
                        rx.input(
                            name="index",
                            placeholder="Filter for a value",
                            default_value=BacnetScanState.point_table_filter.index,
                            width="100%"
                        )
                    ),
                    rx.popover.close(
                        rx.button(
                            "Save",
                            width="100%",
                            type="submit"
                        )
                    )
                ),
                on_submit = BacnetScanState.filter_form_submit
            )
        ),
    )

def notes_filter_popover() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            table_filter_trigger()
        ),
        rx.popover.content(
            rx.form(
                rx.vstack(
                    form_entry.form_entry(
                        "Notes Filter",
                        rx.input(
                            name="notes",
                            placeholder="Filter for a value",
                            default_value=BacnetScanState.point_table_filter.notes,
                            width="100%"
                        )
                    ),
                    rx.popover.close(
                        rx.button(
                            "Save",
                            width="100%",
                            type="submit"
                        )
                    )
                ),
                on_submit = BacnetScanState.filter_form_submit
            )
        ),
    )

def point_column_filter_dialog() -> rx.Component:
    return rx.dialog.root(
            rx.dialog.trigger(
                rx.button(
                        rx.hstack(
                            rx.icon("sliders-horizontal", size=15),
                            rx.text("Toggle Columns"),
                            align="center",
                            spacing="2"
                        ), 
                        size="1",
                    )
            ),
            rx.dialog.content(
                rx.dialog.title("Filter Points Table View"),
                rx.dialog.description(f"Select columns to display or hide."),
                rx.form(
                    rx.vstack(
                        rx.vstack(
                            form_entry.form_entry(
                                "Units",
                                rx.vstack(
                                    rx.checkbox(
                                        name="units", default_checked=BacnetScanState.point_column_filter.units
                                    ),
                                    justify="center",
                                    align="center",
                                    width="100%"
                                ),
                            ),
                            form_entry.form_entry(
                                "BACnet Object Type",
                                rx.vstack(
                                    rx.checkbox(
                                        name="object_type", default_checked=BacnetScanState.point_column_filter.object_type
                                    ),
                                    justify="center",
                                    align="center",
                                    width="100%"
                                ),
                            ),
                            form_entry.form_entry(
                                "Present Value",
                                rx.vstack(
                                    rx.checkbox(
                                        name="present_value", default_checked=BacnetScanState.point_column_filter.present_value
                                    ),
                                    justify="center",
                                    align="center",
                                    width="100%"
                                ),
                            ),
                            form_entry.form_entry(
                                "Writable",
                                rx.vstack(
                                    rx.checkbox(
                                        name="writable", default_checked=BacnetScanState.point_column_filter.writable
                                    ),
                                    justify="center",
                                    align="center",
                                    width="100%"
                                ),
                            ),
                            form_entry.form_entry(
                                "Index",
                                rx.vstack(
                                    rx.checkbox(
                                        name="index", default_checked=BacnetScanState.point_column_filter.index
                                    ),
                                    justify="center",
                                    align="center",
                                    width="100%"
                                ),
                            ),
                            form_entry.form_entry(
                                "Notes",
                                rx.vstack(
                                    rx.checkbox(
                                        name="notes", default_checked=BacnetScanState.point_column_filter.notes
                                    ),
                                    justify="center",
                                    align="center",
                                    width="100%"
                                ),
                            ),
                            margin_top="24px",
                            spacing="3",
                            height="100%",
                            justify="center",
                            align="center",
                            width="100%"
                        ),
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
                                    "Save",
                                    variant="soft",
                                    size="2",
                                    type="submit"
                                ),
                            ),
                            width="100%",
                            justify="between",
                            spacing="2"
                        ),
                        spacing="6",
                        width="100%"
                    ),
                    on_submit=BacnetScanState.save_point_table_filters
                ),
                on_close_auto_focus=lambda: BacnetScanState.on_selected_points_dialog_close
            )
        )

def device_point_dialog_table_headers() -> rx.Component:
    return rx.fragment(
        rx.table.column_header_cell("Point Name"),
        rx.table.column_header_cell("VOLTTRON Point Name"),
        rx.table.column_header_cell("Units"),
        rx.table.column_header_cell("BACnet Object Type"),
        rx.table.column_header_cell("Present Value"),
        rx.table.column_header_cell("Writable"),
        rx.table.column_header_cell("Index"),
        rx.table.column_header_cell("Notes"),
    )

def device_point_table_headers() -> rx.Component:
    return rx.fragment(
        rx.cond(
            BacnetScanState.point_column_filter.units,
            rx.table.column_header_cell(
                rx.hstack(
                    rx.text("Units"),
                    rx.hstack(
                        units_filter_popover(),
                        rx.cond(
                            BacnetScanState.point_table_filter.units != "",
                            filter_badge(
                                BacnetScanState.point_table_filter.units,
                                on_click=lambda: BacnetScanState.clear_point_filter("units"),
                            )
                        ),
                        wrap="wrap"
                    ),
                    align="center",
                    spacing="2"
                )
            )
        ),
        rx.cond(
            BacnetScanState.point_column_filter.object_type,
            rx.table.column_header_cell(
                rx.hstack(
                    rx.text("BACnet Object Type"),
                    rx.hstack(
                        object_type_filter_popover(),
                        rx.cond(
                            BacnetScanState.point_table_filter.object_type != "",
                            filter_badge(
                                BacnetScanState.point_table_filter.object_type,
                                on_click=lambda: BacnetScanState.clear_point_filter("object_type"),
                            )
                        ),
                        wrap="wrap"
                    ),
                    align="center",
                    spacing="2"
                )
            )
        ),
        rx.cond(
            BacnetScanState.point_column_filter.present_value,
            rx.table.column_header_cell(
                rx.hstack(
                    rx.text("Present Value"),
                    rx.hstack(
                        present_value_filter_popover(),
                        rx.cond(
                            BacnetScanState.point_table_filter.present_value != "",
                            filter_badge(
                                BacnetScanState.point_table_filter.present_value,
                                on_click=lambda: BacnetScanState.clear_point_filter("present_value"),
                            )
                        ),
                        wrap="wrap"
                    ),
                    align="center",
                    spacing="2"
                )
            )
        ),
        rx.cond(
            BacnetScanState.point_column_filter.writable,
            rx.table.column_header_cell(
                rx.hstack(
                    rx.text("Writable"),
                    rx.hstack(
                        writable_filter_popover(),
                        rx.cond(
                            BacnetScanState.point_table_filter.writable != "",
                            filter_badge(
                                BacnetScanState.point_table_filter.writable,
                                on_click=lambda: BacnetScanState.clear_point_filter("writable"),
                            )
                        ),
                        wrap="wrap"
                    ),
                    align="center",
                    spacing="2"
                )
            )
        ),
        rx.cond(
            BacnetScanState.point_column_filter.index,
            rx.table.column_header_cell(
                rx.hstack(
                    rx.text("Index"),
                    rx.hstack(
                        index_filter_popover(),
                        rx.cond(
                            BacnetScanState.point_table_filter.index != "",
                            filter_badge(
                                BacnetScanState.point_table_filter.index,
                                on_click=lambda: BacnetScanState.clear_point_filter("index"),
                            )
                        ),
                        wrap="wrap"
                    ),
                    align="center",
                    spacing="2"
                )
            )
        ),
        rx.cond(
            BacnetScanState.point_column_filter.notes,
            rx.table.column_header_cell(
                rx.hstack(
                    rx.text("Notes"),
                    rx.hstack(
                        notes_filter_popover(),
                        rx.cond(
                            BacnetScanState.point_table_filter.notes != "",
                            filter_badge(
                                BacnetScanState.point_table_filter.notes,
                                on_click=lambda: BacnetScanState.clear_point_filter("notes"),
                            )
                        ),
                        wrap="wrap"
                    ),
                    align="center",
                    spacing="2"
                )
            ),
        )
    )

def selected_points_pagination() -> rx.Component:
    return rx.hstack(
        rx.button(
            rx.icon(
                "chevron-left",
                size=20
            ),
            disabled=~BacnetScanState.selected_points_has_prev_page,
            on_click=lambda: BacnetScanState.selected_points_prev_page(),
            size="1"
        ),
        rx.text(f"Page {BacnetScanState.selected_points_page_number}/{BacnetScanState.selected_points_total_pages}"),
        rx.button(
            rx.icon(
                "chevron-right",
                size=20
            ),
            disabled=~BacnetScanState.selected_points_has_next_page,
            on_click=lambda: BacnetScanState.selected_points_next_page(),
            size="1"
        ),
        width="100%",
        justify="center",
        align="center"
    )

def show_selected_points_table() -> rx.Component:
    def show_row(point: BACnetDevicePointModelView) -> rx.Component:
        return rx.table.row(
            rx.table.cell(point.device_name),
            rx.table.cell(point.volttron_point_name),
            rx.table.cell(point.units),
            rx.table.cell(point.object_type),
            rx.table.cell(point.present_value),
            rx.table.cell(
                rx.cond(
                    point.writable,
                    true_writable_badge(),
                    false_writable_badge()
                )
            ),
            rx.table.cell(point.index),
            rx.table.cell(point.notes)
        )
    
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                device_point_dialog_table_headers(),
            ),
        ),
        rx.table.body(
            rx.foreach(
                BacnetScanState.paginated_selected_points,
                show_row
            )
        )
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

def true_writable_badge() -> rx.Component:
    return rx.badge(
        "TRUE",
        color_scheme="blue",
        padding=".25rem .5rem",
        border_radius=".5rem"
    )

def false_writable_badge() -> rx.Component:
    return rx.badge(
        "FALSE",
        color_scheme="gray",
        padding=".25rem .5rem",
        border_radius=".5rem"
    )

def present_value_cell(point: BACnetDevicePointModelView, index: int) -> rx.Component:
    return rx.table.cell(
        rx.hstack(
            rx.cond(
                point.present_value_editing,
                rx.fragment(
                    rx.text_field(
                        value=point.present_value,
                        size="1",
                        on_change=lambda v: BacnetScanState.handle_present_value_edit(index, v)
                    ),
                    rx.button(
                        rx.icon("save", size=12),
                        size="1",
                        on_click=lambda: BacnetScanState.save_device_point_present_value_edit(index)
                    ),
                    rx.button(
                        rx.icon("x", size=12),
                        size="1",
                        color_scheme="red",
                        on_click=lambda: BacnetScanState.cancel_device_point_present_value_edit(index)
                    )
                ),
                rx.fragment(
                    rx.text(point.present_value),
                    rx.button(
                        rx.icon("pencil", size=12),
                        size="1",
                        disabled=rx.cond(
                            point.writable,
                            False,
                            True
                        ),
                        on_click=lambda: BacnetScanState.enable_device_point_present_value_edit(index)
                    )
                )
            ),
            spacing="2"
        )
    )


def volttron_point_name_cell(point: BACnetDevicePointModelView, index: int) -> rx.Component:
    return rx.table.cell(
        rx.hstack(
            rx.checkbox(
                on_change=lambda checked: BacnetScanState.handle_device_check(index, checked), 
                checked=point.selected
            ),
            rx.hstack(
                rx.cond(
                    point.volttron_point_name_editing,
                    rx.fragment(
                        rx.text_field(
                            value=point.volttron_point_name,
                            size="1",
                            on_change=lambda v: BacnetScanState.handle_volttron_point_name_value_edit(index, v)
                        ),
                        rx.button(
                            rx.icon("save", size=12),
                            size="1",
                            on_click=lambda: BacnetScanState.save_device_point_volttron_point_name_value_edit(index)
                        ),
                        rx.button(
                            rx.icon("x", size=12),
                            size="1",
                            color_scheme="red",
                            on_click=lambda: BacnetScanState.cancel_device_point_volttron_point_name_value_edit(index)
                        )
                    ),
                    rx.fragment(
                        rx.text(point.volttron_point_name),
                        rx.button(
                            rx.icon("pencil", size=12),
                            size="1",
                            on_click=lambda: BacnetScanState.enable_device_point_volttron_point_name_value_edit(index)
                        )
                    )
                ),
                spacing="2"
            ),
            spacing="4"
        )
    )

def device_point_table_pagination() -> rx.Component:
    return rx.hstack(
        rx.button(
            rx.icon(
                "chevron-left",
                size=20
            ),
            disabled=~BacnetScanState.prev_page_allowed,
            on_click=lambda: BacnetScanState.prev_point_page(),
            size="1"
        ),
        rx.text(f"Page {BacnetScanState.points_table_page_number}/{BacnetScanState.total_pages}"),
        rx.button(
            rx.icon(
                "chevron-right",
                size=20
            ),
            disabled=~BacnetScanState.next_page_allowed,
            on_click=lambda: BacnetScanState.next_point_page(),
            size="1"
        ),
        width="100%",
        justify="center",
        align="center"
    )

def show_device_point(point_tuple: tuple[int, BACnetDevicePointModelView], index: int) -> rx.Component:
    point = point_tuple[1]
    return rx.table.row(
        volttron_point_name_cell(point, index),
        rx.cond(
            BacnetScanState.point_column_filter.units,
            rx.table.cell(point.units)
        ),
        rx.cond(
            BacnetScanState.point_column_filter.object_type,
            rx.table.cell(point.object_type)
        ),
        rx.cond(
            BacnetScanState.point_column_filter.present_value,
            present_value_cell(point, index)
        ),
        rx.cond(
            BacnetScanState.point_column_filter.writable,
            rx.table.cell(
                rx.button(
                    rx.cond(
                    point.writable,
                        true_writable_badge(),
                        false_writable_badge()
                    ),
                    disabled=point.never_writable,
                    variant="ghost",
                    padding="0px",
                    cursor=rx.cond(
                        point.never_writable,
                        "not-allowed",
                        "pointer"
                    ),
                    on_click=lambda: BacnetScanState.flip_device_point_writable(index)
                )
            )
        ),
        rx.cond(
            BacnetScanState.point_column_filter.index,
            rx.table.cell(point.index)
        ),
        rx.cond(
            BacnetScanState.point_column_filter.notes,
            rx.table.cell(point.notes)
        ),
    )

def show_device(device: BACnetDeviceModelView, index: int) -> rx.Component:
    return rx.fragment(
        rx.table.row(
            rx.table.cell(device.object_name),
            rx.table.cell(device.deviceIdentifier),
            rx.table.cell(device.scanned_ip_target),
            class_name=rx.cond(
                device.device_instance == BacnetScanState.selected_device.device_instance,
                "csv_data_cell active",
                "csv_data_cell"
            ),
            on_click=lambda: BacnetScanState.handle_device_row_click(index)
        ),
        rx.cond(
            # TODO have a cond for if there are not points (for whatever--reason may help with debugging tbh)
            device.device_instance == BacnetScanState.selected_device.device_instance,
            rx.table.row(
                rx.table.cell(
                    rx.vstack(
                        rx.vstack(
                            rx.text("Device Points", size="1", weight="bold"),
                            rx.text(f"Select points to export to CSV or create a registry config file", size="1", color="gray"),
                            rx.text(f"{BacnetScanState.selected_points.length()} points selected", size="1", color="gray"),
                            spacing="1",
                            margin_bottom="12px"
                        ),
                        rx.hstack(
                            point_column_filter_dialog(),
                            rx.hstack(
                                export_points_dialog(),
                                add_to_registry_config_file_dialog(),
                                spacing="2"
                            ),
                            width="100%",
                            justify="between"
                        ),
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell(
                                        rx.hstack(
                                            rx.hstack(
                                                rx.checkbox(
                                                    checked=BacnetScanState.selected_device.select_all_points,
                                                    on_change=BacnetScanState.toggle_select_all_points
                                                ),
                                                rx.text("VOLTTRON Point Name", weight="bold"),
                                                spacing="4"
                                            ),
                                            rx.hstack(
                                                volttron_point_name_filter_popover(),
                                                rx.cond(
                                                    BacnetScanState.point_table_filter.volttron_point_name != "",
                                                    filter_badge(
                                                        BacnetScanState.point_table_filter.volttron_point_name,
                                                        on_click=lambda: BacnetScanState.clear_point_filter("volttron_point_name"),
                                                    )
                                                ),
                                                wrap="wrap"
                                            ),
                                            align="center",
                                            spacing="2"
                                        )
                                    ),
                                    device_point_table_headers(),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    BacnetScanState.points_to_load,
                                    show_device_point
                                ),
                            ),
                            width="100%",
                            border="1px solid",
                            border_color="#272727FF",
                            border_radius=".5rem",
                        ),
                        device_point_table_pagination(),
                        spacing="2",
                        padding="1em",
                        border_radius="6px",
                    ),
                    background_color="#1B1B1B8B",
                    col_span=3
                )
            )
        )
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
                            rx.icon("alert-triangle", size=16, color="orange"),
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


@rx.page(route="/tools/bacnet_scan", on_load=ToolState.start_tool("bacnet_scan_api"))
def bacnet_scan_page() -> rx.Component:
    return app_layout_sidebar.app_layout_sidebar(
        render()
    )
