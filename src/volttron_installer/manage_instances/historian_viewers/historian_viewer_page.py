"""
Unified historian viewer page.

Queries time-series data through the volttron-lib-web VUI REST API — no raw
database file downloads or direct DB connections.  Requires the VOLTTRON web
service and at least one historian agent to be running.
"""

import csv
import io
from datetime import datetime

from nicegui import ui
from volttron_installer.dark import dark_mode_control
from volttron_installer import db
from volttron_installer.manage_instances.historian_viewers import rest_historian
from volttron_installer.manage_instances.historian_viewers.rest_historian import (
    HistorianViewerError,
)


def show_page(instance_name: str):
    dark = dark_mode_control()

    instances = db.get_instances()
    instance = next(
        (inst for inst in instances if inst.get("name") == instance_name), None
    )

    if not instance:
        with ui.column().classes("w-full items-center min-h-screen py-8 px-4"):
            ui.label(f"Instance '{instance_name}' not found.").classes(
                "text-red text-xl font-bold"
            )
            ui.button(
                "Back to Instances",
                icon="arrow_back",
                on_click=lambda: ui.navigate.to("/instances"),
            ).props("outline")
        return

    # ── State ──────────────────────────────────────────────────────────────────
    historians: list[str] = []
    selected_historian: str | None = None

    all_topics: list[str] = []
    filtered_topics: list[str] = []
    selected_topic: str | None = None

    start_dt: str = ""       # ISO 8601 string or "" (means "no filter")
    end_dt: str = ""
    order_value: str = "LAST_TO_FIRST"
    count_value: int = 500
    skip: int = 0

    page_data: dict = {"columns": [], "rows": [], "metadata": {}, "returned_count": 0}

    # ── UI element references ──────────────────────────────────────────────────
    historian_select = None
    search_input = None
    topic_list_container = None
    active_topic_label = None
    metadata_caption = None
    grid_container = None
    prev_btn = None
    next_btn = None
    range_label = None

    # ── Helpers ────────────────────────────────────────────────────────────────

    def show_loading(message: str = "Loading..."):
        if not grid_container:
            return
        grid_container.clear()
        with grid_container:
            with ui.column().classes(
                "w-full items-center justify-center py-16 gap-4"
            ):
                ui.spinner(size="lg")
                ui.label(message).classes("text-grey-5 text-sm")

    def show_empty(message: str):
        if not grid_container:
            return
        grid_container.clear()
        with grid_container:
            ui.label(message).classes("text-grey-5 text-center py-8 text-sm")

    def render_topic_list():
        """Re-render the sidebar topic list, highlighting the active topic."""
        if not topic_list_container:
            return
        topic_list_container.clear()
        with topic_list_container:
            if not filtered_topics:
                ui.label("No topics found.").classes("text-grey-5 text-sm px-2 py-1")
                return
            for t in filtered_topics:
                is_active = t == selected_topic
                row_classes = (
                    "w-full flex items-center gap-2 px-3 py-2 rounded cursor-pointer "
                    + (
                        "bg-primary text-white"
                        if is_active
                        else "hover:bg-grey-2 dark:hover:bg-grey-8"
                    )
                )
                with ui.row().classes(row_classes).on(
                    "click", lambda _, name=t: on_topic_change(name)
                ).tooltip(t):
                    ui.icon("show_chart").classes(
                        "text-sm "
                        + ("text-white" if is_active else "text-primary")
                    )
                    # Truncate long topic strings to keep the sidebar readable
                    label_text = t if len(t) <= 42 else f"…{t[-40:]}"
                    ui.label(label_text).classes("text-sm font-medium truncate")

    def _update_pagination_controls():
        rows_on_page = page_data["returned_count"]
        first = skip + 1 if rows_on_page > 0 else 0
        last = skip + rows_on_page
        if range_label:
            range_label.text = f"Rows {first}–{last}" if rows_on_page > 0 else "No rows"
        if prev_btn:
            prev_btn.enabled = skip > 0
        if next_btn:
            # If the page was full (returned exactly count_value rows) there may be more.
            next_btn.enabled = rows_on_page >= count_value

    def update_grid():
        if not grid_container:
            return
        grid_container.clear()
        with grid_container:
            if not page_data["columns"]:
                ui.label("No data available.").classes(
                    "text-grey-5 text-center py-8"
                )
                return

            columns = [
                {
                    "name": col,
                    "label": col,
                    "field": col,
                    "sortable": True,
                    "align": "left",
                }
                for col in page_data["columns"]
            ]

            table = ui.table(
                columns=columns,
                rows=page_data["rows"],
                row_key=page_data["columns"][0],
                pagination={"rowsPerPage": 50},
            ).classes("w-full")
            table.add_slot(
                "body-cell",
                """
                <q-td :props="props">
                    <span style="white-space: pre-wrap; word-break: break-all;">{{ props.value }}</span>
                </q-td>
            """,
            )

        # Update the metadata caption
        meta = page_data.get("metadata") or {}
        if metadata_caption:
            parts = []
            if meta.get("units"):
                parts.append(f"Units: {meta['units']}")
            if meta.get("type"):
                parts.append(f"Type: {meta['type']}")
            if meta.get("tz"):
                parts.append(f"TZ: {meta['tz']}")
            metadata_caption.text = "  ·  ".join(parts) if parts else ""
            metadata_caption.visible = bool(parts)

        _update_pagination_controls()

    # ── Data loading ───────────────────────────────────────────────────────────

    async def load_historians():
        nonlocal historians, selected_historian
        show_loading("Connecting to VOLTTRON web service…")
        try:
            historians = await rest_historian.list_historians(instance)
            if not historians:
                if historian_select:
                    historian_select.options = []
                    historian_select.value = None
                show_empty(
                    "No running historian found on this platform.\n"
                    "Start a historian agent and refresh."
                )
                return

            if historian_select:
                historian_select.options = historians
                default = (
                    next(
                        (h for h in historians if "historian" in h.lower()),
                        historians[0],
                    )
                )
                historian_select.value = default
            await on_historian_change(
                next(
                    (h for h in historians if "historian" in h.lower()),
                    historians[0],
                )
            )
        except HistorianViewerError as exc:
            show_empty(str(exc))
            ui.notify(str(exc), type="negative", timeout=8000)
        except Exception as exc:
            show_empty(f"Unexpected error: {exc}")
            ui.notify(f"Error connecting to web service: {exc}", type="negative")

    async def on_historian_change(historian: str | None):
        nonlocal selected_historian, all_topics, filtered_topics, selected_topic, skip
        selected_historian = historian
        all_topics = []
        filtered_topics = []
        selected_topic = None
        skip = 0

        if topic_list_container:
            topic_list_container.clear()
        if active_topic_label:
            active_topic_label.text = "No topic selected"
        if metadata_caption:
            metadata_caption.text = ""
            metadata_caption.visible = False

        if not historian:
            return

        show_loading(f"Loading topics from {historian}…")
        try:
            all_topics = await rest_historian.list_topics(instance, historian)
            if not all_topics:
                show_empty("No topics recorded yet.")
                return
            # Apply any existing search filter
            filter_topics()
            # Auto-select the first topic
            if filtered_topics:
                await on_topic_change(filtered_topics[0])
        except HistorianViewerError as exc:
            show_empty(str(exc))
            ui.notify(str(exc), type="negative", timeout=8000)
        except Exception as exc:
            show_empty(f"Error loading topics: {exc}")
            ui.notify(f"Error loading topics: {exc}", type="negative")

    def filter_topics():
        """Recompute filtered_topics from all_topics + search box."""
        nonlocal filtered_topics
        query = (search_input.value or "").strip().lower() if search_input else ""
        filtered_topics = (
            [t for t in all_topics if query in t.lower()] if query else list(all_topics)
        )
        render_topic_list()

    async def on_topic_change(topic: str | None):
        nonlocal selected_topic, skip
        if not topic:
            return
        selected_topic = topic
        skip = 0
        render_topic_list()
        if active_topic_label:
            active_topic_label.text = topic
        await load_page()

    async def load_page():
        nonlocal page_data
        if not selected_historian or not selected_topic:
            return
        show_loading(f"Loading data for {selected_topic}…")
        try:
            page_data = await rest_historian.query_topic(
                instance,
                selected_historian,
                selected_topic,
                start=start_dt or None,
                end=end_dt or None,
                skip=skip,
                count=count_value,
                order=order_value,
            )
            update_grid()
        except HistorianViewerError as exc:
            show_empty(str(exc))
            ui.notify(str(exc), type="negative", timeout=8000)
        except Exception as exc:
            show_empty(f"Error loading data: {exc}")
            ui.notify(f"Error loading data: {exc}", type="negative")

    async def on_prev():
        nonlocal skip
        skip = max(0, skip - count_value)
        await load_page()

    async def on_next():
        nonlocal skip
        skip += count_value
        await load_page()

    async def on_order_change(value: str):
        nonlocal order_value, skip
        order_value = value
        skip = 0
        await load_page()

    async def on_count_change(value):
        nonlocal count_value, skip
        try:
            count_value = max(1, int(value))
        except (TypeError, ValueError):
            return
        skip = 0
        await load_page()

    # ── Date/time picker helpers ───────────────────────────────────────────────
    # NiceGUI date+time pickers wrapped in a menu button.
    # State is stored in start_dt / end_dt as ISO 8601 strings.

    def _make_dt_button(label: str, get_val, set_val, on_changed):
        """
        Render a compact date+time picker button.
        get_val() returns the current ISO string; set_val(s) updates it.
        on_changed is called (no args) after the user picks a new value.
        """
        with ui.row().classes("items-center gap-1"):
            ui.label(label).classes("text-xs text-grey-6 whitespace-nowrap")
            with ui.button(icon="event").props("flat dense size=sm").tooltip(
                f"Pick {label}"
            ):
                with ui.menu().props("auto-close"):
                    with ui.column().classes("p-2 gap-1"):
                        date_picker = ui.date(
                            value=get_val()[:10] if get_val() else None
                        ).classes("w-48")
                        time_picker = ui.time(
                            value=get_val()[11:19] if len(get_val()) >= 19 else "00:00:00"
                        ).classes("w-48")

                        async def _apply(_d=date_picker, _t=time_picker):
                            d_val = _d.value or ""
                            t_val = _t.value or "00:00:00"
                            if d_val:
                                set_val(f"{d_val}T{t_val}")
                            else:
                                set_val("")
                            await on_changed()

                        ui.button("Apply", on_click=_apply).props(
                            "color=primary dense"
                        )

            # Small clear button shown when a value is set
            def _clear_dt():
                set_val("")

            clear_btn = (
                ui.button(icon="close")
                .props("flat dense size=xs color=grey")
                .on("click", lambda: _clear_dt())
                .tooltip(f"Clear {label}")
            )

    def export_csv():
        if not page_data["rows"]:
            ui.notify("No data to export.", type="warning")
            return
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=page_data["columns"])
        writer.writeheader()
        writer.writerows(page_data["rows"])
        filename = (
            f"{selected_topic.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            if selected_topic
            else "historian_export.csv"
        )
        ui.download(output.getvalue().encode("utf-8"), filename, "text/csv")
        ui.notify("CSV exported.", type="positive")

    # ── Page layout ────────────────────────────────────────────────────────────
    with ui.column().classes("w-full items-center min-h-screen py-8 px-4"):
        with ui.column().classes("w-full max-w-7xl gap-4 mb-4"):

            # Header
            with ui.row().classes("w-full justify-between items-center"):
                with ui.row().classes("items-center gap-3"):
                    ui.button(
                        icon="arrow_back",
                        on_click=lambda: ui.navigate.to(f"/manage/{instance_name}"),
                    ).props("flat round")
                    with ui.column().classes("gap-0"):
                        ui.label("Historian Viewer").classes("text-3xl font-bold")
                        ui.label(f"Instance: {instance_name}").classes("text-grey-6")

                with ui.row().classes("items-center gap-3"):
                    theme_btn = ui.button(on_click=dark.toggle).props("flat round")
                    theme_btn.bind_icon_from(
                        dark,
                        "value",
                        backward=lambda v: "light_mode" if v else "dark_mode",
                    )

            ui.separator()

            with ui.row().classes("w-full gap-5 items-stretch no-wrap"):

                # ── Sidebar ──────────────────────────────────────────────────
                with ui.column().classes("gap-4 py-2 w-80 min-w-80"):

                    ui.label("Historian").classes("font-bold text-lg")
                    historian_select = ui.select(
                        options=[],
                        label="Historian agent",
                        on_change=lambda e: on_historian_change(e.value),
                    ).props("outlined dense").classes("w-full")

                    ui.separator()

                    ui.label("Topics").classes("font-bold text-lg")
                    search_input = ui.input(
                        placeholder="Filter topics…",
                        on_change=lambda _: filter_topics(),
                    ).props("outlined dense clearable").classes("w-full")
                    search_input.props("prepend-icon=search")

                    topic_list_container = ui.column().classes(
                        "w-full gap-1 max-h-[28rem] overflow-y-auto"
                    )

                ui.separator().props("vertical")

                # ── Main content ─────────────────────────────────────────────
                with ui.column().classes("gap-3 py-2 flex-grow min-w-0"):

                    # Active topic label
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("show_chart").classes("text-primary")
                        active_topic_label = ui.label("No topic selected").classes(
                            "font-bold text-base"
                        )

                    # Toolbar: time range + order + count + actions
                    with ui.row().classes("w-full items-center gap-3 flex-wrap"):

                        # Start picker
                        with ui.row().classes("items-center gap-1"):
                            ui.label("Start").classes(
                                "text-xs text-grey-6 whitespace-nowrap"
                            )
                            with ui.button(icon="event_available").props(
                                "flat dense size=sm outline"
                            ).tooltip("Pick start date/time"):
                                with ui.menu():
                                    with ui.column().classes("p-2 gap-1"):
                                        start_date_pick = ui.date().classes("w-48")
                                        start_time_pick = ui.time(
                                            value="00:00:00"
                                        ).classes("w-48")

                                        async def _apply_start(
                                            _d=start_date_pick,
                                            _t=start_time_pick,
                                        ):
                                            nonlocal start_dt, skip
                                            d_val = _d.value or ""
                                            t_val = _t.value or "00:00:00"
                                            start_dt = (
                                                f"{d_val}T{t_val}" if d_val else ""
                                            )
                                            skip = 0
                                            await load_page()

                                        ui.button(
                                            "Apply", on_click=_apply_start
                                        ).props("color=primary dense")
                                        ui.button(
                                            "Clear",
                                            on_click=lambda: _clear_start(),
                                        ).props("flat dense")

                                        def _clear_start():
                                            nonlocal start_dt
                                            start_dt = ""
                                            start_date_pick.value = None

                        # End picker
                        with ui.row().classes("items-center gap-1"):
                            ui.label("End").classes(
                                "text-xs text-grey-6 whitespace-nowrap"
                            )
                            with ui.button(icon="event_busy").props(
                                "flat dense size=sm outline"
                            ).tooltip("Pick end date/time"):
                                with ui.menu():
                                    with ui.column().classes("p-2 gap-1"):
                                        end_date_pick = ui.date().classes("w-48")
                                        end_time_pick = ui.time(
                                            value="23:59:59"
                                        ).classes("w-48")

                                        async def _apply_end(
                                            _d=end_date_pick,
                                            _t=end_time_pick,
                                        ):
                                            nonlocal end_dt, skip
                                            d_val = _d.value or ""
                                            t_val = _t.value or "23:59:59"
                                            end_dt = (
                                                f"{d_val}T{t_val}" if d_val else ""
                                            )
                                            skip = 0
                                            await load_page()

                                        ui.button(
                                            "Apply", on_click=_apply_end
                                        ).props("color=primary dense")
                                        ui.button(
                                            "Clear",
                                            on_click=lambda: _clear_end(),
                                        ).props("flat dense")

                                        def _clear_end():
                                            nonlocal end_dt
                                            end_dt = ""
                                            end_date_pick.value = None

                        # Order selector
                        ui.select(
                            options={
                                "LAST_TO_FIRST": "Newest first",
                                "FIRST_TO_LAST": "Oldest first",
                            },
                            value="LAST_TO_FIRST",
                            on_change=lambda e: on_order_change(e.value),
                        ).props("outlined dense").classes("w-36").tooltip("Sort order")

                        # Count input
                        ui.number(
                            label="Max rows",
                            value=500,
                            min=1,
                            max=10000,
                            step=100,
                            on_change=lambda e: on_count_change(e.value),
                        ).props("outlined dense").classes("w-28").tooltip(
                            "Maximum rows per page"
                        )

                        ui.space()

                        ui.button(
                            icon="refresh", on_click=load_page
                        ).props("flat round color=primary").tooltip("Refresh data")
                        ui.button(
                            "Export CSV",
                            icon="download",
                            on_click=export_csv,
                        ).props("outline color=primary").tooltip(
                            "Export current view to CSV"
                        )

                    # Metadata caption (units/type/tz)
                    metadata_caption = (
                        ui.label("")
                        .classes("text-xs text-grey-6")
                    )
                    metadata_caption.visible = False

                    # Pagination row
                    with ui.row().classes("items-center gap-2"):
                        prev_btn = ui.button(
                            icon="chevron_left", on_click=on_prev
                        ).props("flat round dense").tooltip("Previous page")
                        prev_btn.enabled = False
                        next_btn = ui.button(
                            icon="chevron_right", on_click=on_next
                        ).props("flat round dense").tooltip("Next page")
                        next_btn.enabled = False
                        range_label = ui.label("").classes("text-sm text-grey-6")

                    # Grid
                    grid_container = ui.column().classes("w-full flex-grow")

    # Initial load
    ui.timer(0.1, load_historians, once=True)
