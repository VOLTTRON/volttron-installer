"""
Weather agent SQLite viewer.

Reads directly from the weather agent's local SQLite cache
(volttron-weather-dot-gov-*.agent-data/weather.sqlite) and presents
current observations and hourly forecasts in a browsable table.
"""

import csv
import io
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from nicegui import ui
from volttron_installer.dark import dark_mode_control
from volttron_installer import db

# Weather point columns to show — ordered, human-readable
_WEATHER_COLS = [
    "stationName",
    "textDescription",
    "air_temperature",
    "dew_point_temperature",
    "relative_humidity",
    "wind_speed",
    "wind_from_direction",
    "wind_speed_of_gust",
    "air_pressure_at_mean_sea_level",
    "visibility_in_air",
    "heatIndex",
    "windChill",
    "precipitationLast3Hours",
    "cloud_area_fraction_in_atmosphere_layer",
]


def _find_weather_db(instance: dict) -> Path | None:
    """Return the path to the weather agent's SQLite file, or None if not found."""
    volttron_home = instance.get("volttron_home", "")
    if not volttron_home:
        return None
    agents_dir = Path(volttron_home).expanduser() / "agents"
    if not agents_dir.exists():
        return None
    for agent_dir in agents_dir.iterdir():
        if not agent_dir.is_dir():
            continue
        # Each agent dir contains a versioned subdir; check one level deeper too
        candidates = list(agent_dir.glob("*.agent-data/weather.sqlite"))
        candidates += list(agent_dir.glob("weather.sqlite"))
        for c in candidates:
            if c.exists():
                return c
    return None


def _extract_value(val):
    """Unwrap a NOAA {unitCode, value} dict to a plain scalar."""
    if isinstance(val, dict):
        v = val.get("value")
        unit = val.get("unitCode", "")
        if v is None:
            return None
        # Strip the wmoUnit: prefix for readability
        unit_short = unit.split(":")[-1] if ":" in unit else unit
        return f"{v} {unit_short}".strip()
    if isinstance(val, list):
        # cloud layers — just summarise
        return "; ".join(
            f"{item.get('amount','?')} @ {item.get('base',{}).get('value','?')} m"
            for item in val
            if isinstance(item, dict)
        ) or str(val)
    return val


def _rows_from_current(db_path: Path, station_filter: str | None = None) -> tuple[list[str], list[dict]]:
    """Query get_current_weather, unpack POINTS, return (columns, rows)."""
    cols = ["observation_time", "station"] + _WEATHER_COLS
    rows = []
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        if station_filter:
            cur.execute(
                "SELECT LOCATION, OBSERVATION_TIME, POINTS FROM get_current_weather WHERE LOCATION = ? ORDER BY OBSERVATION_TIME DESC",
                (station_filter,),
            )
        else:
            cur.execute(
                "SELECT LOCATION, OBSERVATION_TIME, POINTS FROM get_current_weather ORDER BY OBSERVATION_TIME DESC"
            )
        for loc_json, obs_time, points_json in cur.fetchall():
            try:
                points = json.loads(points_json)
            except Exception:
                points = {}
            location = json.loads(loc_json) if isinstance(loc_json, str) else loc_json
            station = location.get("station", str(loc_json))
            row = {"observation_time": str(obs_time), "station": station}
            for col in _WEATHER_COLS:
                row[col] = _extract_value(points.get(col))
            rows.append(row)
        conn.close()
    except Exception as exc:
        raise RuntimeError(f"Failed to read weather database: {exc}") from exc
    return cols, rows


def _rows_from_forecast(db_path: Path, station_filter: str | None = None) -> tuple[list[str], list[dict]]:
    """Query get_hourly_forecast, unpack POINTS, return (columns, rows)."""
    cols = ["forecast_time", "generation_time", "station"] + _WEATHER_COLS
    rows = []
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        if station_filter:
            cur.execute(
                "SELECT LOCATION, GENERATION_TIME, FORECAST_TIME, POINTS FROM get_hourly_forecast WHERE LOCATION = ? ORDER BY FORECAST_TIME ASC",
                (station_filter,),
            )
        else:
            cur.execute(
                "SELECT LOCATION, GENERATION_TIME, FORECAST_TIME, POINTS FROM get_hourly_forecast ORDER BY FORECAST_TIME ASC"
            )
        for loc_json, gen_time, fc_time, points_json in cur.fetchall():
            try:
                points = json.loads(points_json)
            except Exception:
                points = {}
            location = json.loads(loc_json) if isinstance(loc_json, str) else loc_json
            station = location.get("station", str(loc_json))
            row = {"forecast_time": str(fc_time), "generation_time": str(gen_time), "station": station}
            for col in _WEATHER_COLS:
                row[col] = _extract_value(points.get(col))
            rows.append(row)
        conn.close()
    except Exception as exc:
        raise RuntimeError(f"Failed to read weather database: {exc}") from exc
    return cols, rows


def _list_stations(db_path: Path) -> list[str]:
    """Return distinct station IDs from get_current_weather."""
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT LOCATION FROM get_current_weather")
        stations = []
        for (loc_json,) in cur.fetchall():
            loc = json.loads(loc_json) if isinstance(loc_json, str) else {}
            stations.append(loc.get("station", loc_json))
        conn.close()
        return sorted(stations)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def show_page(instance_name: str):
    dark = dark_mode_control()

    instances = db.get_instances()
    instance = next((i for i in instances if i.get("name") == instance_name), None)

    if not instance:
        with ui.column().classes("w-full items-center min-h-screen py-8 px-4"):
            ui.label(f"Instance '{instance_name}' not found.").classes("text-red text-xl font-bold")
            ui.button("Back to Instances", icon="arrow_back", on_click=lambda: ui.navigate.to("/instances")).props("outline")
        return

    db_path = _find_weather_db(instance)

    # ── State ─────────────────────────────────────────────────────────────────
    view_mode = "current"   # "current" or "forecast"
    selected_station: str | None = None
    stations: list[str] = []
    page_data: dict = {"columns": [], "rows": []}

    # ── UI refs ────────────────────────────────────────────────────────────────
    station_select_ref = None
    grid_container = None
    row_count_label = None
    db_path_label = None

    def show_loading(msg="Loading…"):
        if not grid_container:
            return
        grid_container.clear()
        with grid_container:
            with ui.column().classes("w-full items-center justify-center py-16 gap-4"):
                ui.spinner(size="lg")
                ui.label(msg).classes("text-grey-5 text-sm")

    def show_empty(msg):
        if not grid_container:
            return
        grid_container.clear()
        with grid_container:
            ui.label(msg).classes("text-grey-5 text-center py-8 text-sm")

    def update_grid():
        if not grid_container:
            return
        grid_container.clear()
        cols_list = page_data.get("columns", [])
        rows_list = page_data.get("rows", [])

        if row_count_label:
            row_count_label.text = f"{len(rows_list)} row{'s' if len(rows_list) != 1 else ''}"

        if not cols_list:
            show_empty("No data available.")
            return

        with grid_container:
            columns = [
                {"name": c, "label": c.replace("_", " ").title(), "field": c, "sortable": True, "align": "left"}
                for c in cols_list
            ]
            table = ui.table(
                columns=columns,
                rows=rows_list,
                row_key=cols_list[0],
                pagination={"rowsPerPage": 25},
            ).classes("w-full")
            table.add_slot(
                "body-cell",
                """
                <q-td :props="props">
                    <span style="white-space: pre-wrap; word-break: break-all; font-size: 0.78rem;">{{ props.value ?? '—' }}</span>
                </q-td>
                """,
            )

    def load_data():
        nonlocal page_data
        if not db_path:
            show_empty("Weather database not found.\nMake sure the weather agent has run at least once.")
            return
        show_loading("Reading weather database…")
        try:
            station_json = (
                json.dumps({"station": selected_station}) if selected_station else None
            )
            if view_mode == "current":
                cols, rows = _rows_from_current(db_path, station_json)
            else:
                cols, rows = _rows_from_forecast(db_path, station_json)
            page_data = {"columns": cols, "rows": rows}
            update_grid()
            if not rows:
                show_empty("No data in this table yet.")
        except Exception as exc:
            show_empty(str(exc))
            ui.notify(str(exc), type="negative", timeout=8000)

    def on_station_change(station: str | None):
        nonlocal selected_station
        selected_station = station
        load_data()

    def on_view_change(mode: str):
        nonlocal view_mode
        view_mode = mode
        load_data()

    def export_csv():
        rows = page_data.get("rows", [])
        cols = page_data.get("columns", [])
        if not rows:
            ui.notify("No data to export.", type="warning")
            return
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        filename = f"weather_{view_mode}_{selected_station or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
                        ui.label("Weather Viewer").classes("text-3xl font-bold")
                        ui.label(f"Instance: {instance_name}").classes("text-grey-6")
                with ui.row().classes("items-center gap-3"):
                    theme_btn = ui.button(on_click=dark.toggle).props("flat round")
                    theme_btn.bind_icon_from(dark, "value", backward=lambda v: "light_mode" if v else "dark_mode")

            ui.separator()

            if not db_path:
                with ui.column().classes("w-full items-center py-20 gap-4"):
                    ui.icon("cloud_off", size="xl", color="grey")
                    ui.label("Weather database not found").classes("text-xl text-grey-6")
                    ui.label(
                        "The weather agent must be installed and have run at least once to create the database."
                    ).classes("text-sm text-grey-6 text-center max-w-md")
                    ui.button("Back", icon="arrow_back", on_click=lambda: ui.navigate.to(f"/manage/{instance_name}")).props("outline")
                return

            # DB path info
            with ui.row().classes("items-center gap-2"):
                ui.icon("storage", color="grey", size="sm")
                ui.label(str(db_path)).classes("text-xs text-grey-6 font-mono")

            with ui.row().classes("w-full gap-5 items-stretch no-wrap"):

                # ── Sidebar ───────────────────────────────────────────────────
                with ui.column().classes("gap-4 py-2 w-64 min-w-64"):

                    ui.label("Data source").classes("font-bold text-lg")
                    ui.select(
                        options={"current": "Current observations", "forecast": "Hourly forecast"},
                        value="current",
                        on_change=lambda e: on_view_change(e.value),
                    ).props("outlined dense").classes("w-full")

                    ui.separator()

                    ui.label("Station").classes("font-bold text-lg")
                    stations = _list_stations(db_path)
                    station_options = {"": "All stations"} | {s: s for s in stations}
                    station_select_ref = ui.select(
                        options=station_options,
                        value="",
                        on_change=lambda e: on_station_change(e.value or None),
                    ).props("outlined dense").classes("w-full")

                ui.separator().props("vertical")

                # ── Main content ──────────────────────────────────────────────
                with ui.column().classes("gap-3 py-2 flex-grow min-w-0"):

                    with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                        ui.icon("cloud", color="primary")
                        row_count_label = ui.label("").classes("text-sm text-grey-6")
                        ui.space()
                        ui.button(icon="refresh", on_click=load_data).props("flat round color=primary").tooltip("Refresh")
                        ui.button("Export CSV", icon="download", on_click=export_csv).props("outline color=primary")

                    grid_container = ui.column().classes("w-full flex-grow")

    # Initial load
    ui.timer(0.1, load_data, once=True)
