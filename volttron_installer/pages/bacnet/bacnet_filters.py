import reflex as rx
from ...state import BacnetScanState
from ...components.form_components import form_entry
from ...components.buttons.tile_icon import tile_icon


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
                on_submit=BacnetScanState.filter_form_submit
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
                on_submit=BacnetScanState.filter_form_submit
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
                on_submit=BacnetScanState.filter_form_submit
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
                on_submit=BacnetScanState.filter_form_submit
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
                on_submit=BacnetScanState.filter_form_submit
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
                on_submit=BacnetScanState.filter_form_submit
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
                on_submit=BacnetScanState.filter_form_submit
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