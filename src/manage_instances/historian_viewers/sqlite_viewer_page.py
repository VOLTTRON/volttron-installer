import csv
import io
from nicegui import ui, binding
from src import db, theme
from src.manage_instances.historian_viewers import sqlite_historian

def show_page(instance_name: str):
    dark_mode = theme.dark_mode()

    instances = db.get_instances()
    instance = next((inst for inst in instances if inst.get("name") == instance_name), None)

    if not instance:
        with ui.column().classes(theme.page_container('py-8 px-4')):
            ui.label(f"Instance '{instance_name}' not found.").classes('text-red text-xl font-bold')
            back_btn = ui.button('Back to Instances', icon='arrow_back', on_click=lambda: ui.navigate.to('/instances')).props('outline')
            binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
        return

    # State variables
    db_files = []
    selected_db = None
    tables = []
    selected_table = None
    table_schema = []
    table_data = {"columns": [], "rows": [], "total_count": 0}

    limit = 500
    offset = 0

    # UI Elements references
    db_select = None
    table_tree = None
    grid_container = None
    ag_grid = None
    pagination_label = None
    table_select = None

    async def load_databases():
        nonlocal db_files, selected_db
        try:
            db_files = await sqlite_historian.find_databases(instance)
            if db_files:
                db_select.options = db_files
                historian_db = next((f for f in db_files if "historian" in f.lower()), db_files[0])
                db_select.value = historian_db
                await on_db_change(historian_db)
            else:
                db_select.options = []
                db_select.value = None
                ui.notify("No SQLite databases found in VOLTTRON_HOME.", type="warning")
        except Exception as e:
            ui.notify(f"Error finding databases: {e}", type="negative")

    async def on_db_change(db_path):
        nonlocal selected_db, tables, selected_table
        selected_db = db_path
        selected_table = None
        tables = []
        if table_tree:
            table_tree._props['nodes'] = []
            table_tree.update()
        if table_select:
            table_select.options = []
            table_select.value = None

        if not db_path:
            return

        try:
            tables = await sqlite_historian.list_tables(instance, db_path)
            if table_select:
                table_select.options = tables

            tree_nodes = [
                {"id": t, "label": t, "icon": "table_chart", "children": []}
                for t in tables
            ]
            if table_tree:
                table_tree._props['nodes'] = tree_nodes
                table_tree.update()

            if tables:
                default_table = next((t for t in tables if t.lower() in ["data", "topics"]), tables[0])
                if table_select:
                    table_select.value = default_table
                await on_table_change(default_table)
        except Exception as e:
            ui.notify(f"Error loading tables: {e}", type="negative")

    async def on_table_change(table_name):
        nonlocal selected_table, offset
        selected_table = table_name
        offset = 0
        await load_table_data()

    async def load_table_data():
        nonlocal table_data, table_schema
        if not selected_db or not selected_table:
            return

        try:
            table_schema = await sqlite_historian.get_table_schema(instance, selected_db, selected_table)
            table_data = await sqlite_historian.query_table(
                instance, selected_db, selected_table, limit=limit, offset=offset
            )
            total_count = table_data["total_count"]
            if pagination_label:
                pagination_label.text = f"Total: {total_count} rows"
            update_grid()
        except Exception as e:
            ui.notify(f"Error loading table data: {e}", type="negative")

    def update_grid():
        nonlocal ag_grid
        if not grid_container:
            return

        grid_container.clear()
        with grid_container:
            if not table_data["columns"]:
                ui.label("No data available").classes('text-grey-5 text-center py-8')
                return

            columns = [
                {"name": col, "label": col, "field": col, "sortable": True, "align": "left"}
                for col in table_data["columns"]
            ]

            ag_grid = ui.table(
                columns=columns,
                rows=table_data["rows"],
                row_key=table_data["columns"][0],
                pagination={"rowsPerPage": 50}
            ).classes('w-full')
            ag_grid.add_slot('body-cell', '''
                <q-td :props="props">
                    <span style="white-space: pre-wrap; word-break: break-all;">{{ props.value }}</span>
                </q-td>
            ''')

    def export_csv():
        if not table_data["rows"]:
            ui.notify("No data to export", type="warning")
            return

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=table_data["columns"])
        writer.writeheader()
        writer.writerows(table_data["rows"])
        ui.download(output.getvalue().encode('utf-8'), f"{selected_table}_export.csv", "text/csv")
        ui.notify("CSV Exported successfully", type="positive")

    # Page Layout
    with ui.column().classes(theme.page_container('py-8 px-4')):
        with ui.column().classes('w-full max-w-6xl gap-4 mb-4'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-3'):
                    back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to(f'/manage/{instance_name}')).props('flat round')
                    binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    with ui.column().classes('gap-0'):
                        ui.label('SQLite Viewer').classes('text-3xl font-bold')
                        ui.label(f'Instance: {instance_name}').classes(theme.muted())

                with ui.row().classes('items-center gap-3'):
                    theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
                    theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
                    binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')

            ui.separator()

            with ui.row().classes('w-full gap-5 items-stretch no-wrap'):
                # Sidebar
                with ui.column().classes('gap-4 py-2 w-80 min-w-80'):
                    ui.label('Select Database').classes('font-bold text-lg')
                    db_select = ui.select(
                        options=[],
                        label='SQLite File',
                        on_change=lambda e: on_db_change(e.value)
                    ).props('outlined dense').classes('w-full')

                    ui.separator()

                    ui.label('Tables').classes('font-bold text-lg')
                    table_tree = ui.tree(
                        nodes=[],
                        label_key='label',
                        on_select=lambda e: on_table_change(e.value) if e.value in tables else None
                    ).classes('w-full max-h-96 overflow-y-auto')

                ui.separator().props('vertical')

                # Main Content Area
                with ui.column().classes('gap-4 py-2 flex-grow min-w-0'):
                    with ui.row().classes('w-full items-center gap-3'):
                        table_select = ui.select(
                            options=[],
                            label='Active Table',
                            on_change=lambda e: on_table_change(e.value) if e.value else None
                        ).props('outlined dense').classes('w-64')

                        ui.button(icon='refresh', on_click=load_table_data).props('flat round color="primary"').tooltip('Refresh data')
                        ui.button('Export CSV', icon='download', on_click=export_csv).props('outline color="primary"').tooltip('Export current view to CSV')
                        ui.space()
                        pagination_label = ui.label('No table selected').classes('text-sm')

                    grid_container = ui.column().classes('w-full flex-grow')

    # Initial load
    ui.timer(0.1, load_databases, once=True)
