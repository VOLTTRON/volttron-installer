import reflex as rx
from ...state import BacnetScanState
from ...model_views import BACnetDeviceModelView, BACnetDevicePointModelView
from .bacnet_filters import (
    filter_badge,
    units_filter_popover,
    object_type_filter_popover,
    present_value_filter_popover,
    writable_filter_popover,
    index_filter_popover,
    notes_filter_popover,
    volttron_point_name_filter_popover,
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
    # Local imports to avoid circular dependency with bacnet_dialogs
    from .bacnet_dialogs import export_points_dialog, add_to_registry_config_file_dialog
    from .bacnet_filters import point_column_filter_dialog

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