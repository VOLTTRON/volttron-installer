import csv
import io
from nicegui import ui, binding
from src import db, theme
from src.manage_instances.historian_viewers import postgresql_historian
from src.manage_instances import agent_management

# Default connection params matching the PostgreSQL Historian config template
_DEFAULT_PARAMS = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "test_historian",
    "user": "historian",
    "password": "historian",
}


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

    # ── State ────────────────────────────────────────────────────────────────
    conn_params = {}          # active connection params dict
    tables = []
    selected_table = None
    table_data = {"columns": [], "rows": [], "total_count": 0}
    limit = 500
    offset = 0

    # ── UI element references ─────────────────────────────────────────────────
    connection_summary = None   # ui.column shown when params are auto-discovered
    connection_form = None      # ui.column shown when params need manual entry
    host_input = None
    port_input = None
    dbname_input = None
    user_input = None
    password_input = None
    connect_btn = None
    table_tree = None
    table_select = None
    grid_container = None
    ag_grid = None
    pagination_label = None
    status_label = None

    # ── Discovery ────────────────────────────────────────────────────────────

    async def _find_postgres_historian_identity() -> str | None:
        """Try to find a running postgresql historian agent VIP identity."""
        try:
            agents = await agent_management.list_agents(instance)
            for agent in agents:
                identity = agent.get("identity", "")
                name = agent.get("name", "")
                if "postgresql" in identity.lower() or "postgresql" in name.lower():
                    return identity
            # Fallback: any historian that isn't sqlite
            for agent in agents:
                identity = agent.get("identity", "")
                name = agent.get("name", "")
                if "historian" in identity.lower() or "historian" in name.lower():
                    if "sqlite" not in identity.lower() and "sqlite" not in name.lower():
                        return identity
        except Exception:
            pass
        return None

    async def load_connection():
        nonlocal conn_params
        if status_label:
            status_label.text = "Discovering connection…"

        identity = await _find_postgres_historian_identity()
        discovered = None
        if identity:
            discovered = await postgresql_historian.discover_connection(instance, identity)

        if discovered:
            conn_params = discovered
            # Show summary, hide form
            _populate_form(conn_params)
            if connection_summary:
                connection_summary.set_visibility(True)
            if connection_form:
                connection_form.set_visibility(False)
            if status_label:
                status_label.text = f"Auto-discovered from agent: {identity}"
            await connect_to_db()
        else:
            # Fall back to defaults shown in editable form
            conn_params = dict(_DEFAULT_PARAMS)
            _populate_form(conn_params)
            if connection_summary:
                connection_summary.set_visibility(False)
            if connection_form:
                connection_form.set_visibility(True)
            if status_label:
                status_label.text = "Enter connection details and click Connect."

    def _populate_form(params: dict):
        if host_input:
            host_input.value = str(params.get("host", "127.0.0.1"))
        if port_input:
            port_input.value = str(params.get("port", 5432))
        if dbname_input:
            dbname_input.value = str(params.get("dbname", ""))
        if user_input:
            user_input.value = str(params.get("user", ""))
        if password_input:
            password_input.value = str(params.get("password", ""))

    def _params_from_form() -> dict:
        return {
            "host": host_input.value.strip() if host_input else "127.0.0.1",
            "port": int(port_input.value) if port_input and port_input.value else 5432,
            "dbname": dbname_input.value.strip() if dbname_input else "",
            "user": user_input.value.strip() if user_input else "",
            "password": password_input.value if password_input else "",
        }

    # ── Connect / table loading ───────────────────────────────────────────────

    async def connect_to_db():
        nonlocal tables, selected_table, conn_params
        if connection_form and connection_form.visible:
            conn_params = _params_from_form()

        selected_table = None
        tables = []
        if table_tree:
            table_tree._props['nodes'] = []
            table_tree.update()
        if table_select:
            table_select.options = []
            table_select.value = None

        try:
            tables = await postgresql_historian.list_tables(instance, conn_params)
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
            else:
                ui.notify("Connected — no tables found in public schema.", type="warning")
        except Exception as e:
            ui.notify(f"Connection failed: {e}", type="negative")

    async def on_table_change(table_name: str):
        nonlocal selected_table, offset
        selected_table = table_name
        offset = 0
        await load_table_data()

    async def load_table_data():
        nonlocal table_data
        if not conn_params or not selected_table:
            return
        try:
            table_data = await postgresql_historian.query_table(
                instance, conn_params, selected_table, limit=limit, offset=offset
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
                pagination={"rowsPerPage": 50},
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
        ui.notify("CSV exported successfully", type="positive")

    # ── Page layout ───────────────────────────────────────────────────────────
    with ui.column().classes(theme.page_container('py-8 px-4')):
        # Header
        with ui.column().classes('w-full max-w-6xl gap-4 mb-4'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-3'):
                    back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to(f'/manage/{instance_name}')).props('flat round')
                    binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    with ui.column().classes('gap-0'):
                        ui.label('PostgreSQL Viewer').classes('text-3xl font-bold')
                        ui.label(f'Instance: {instance_name}').classes(theme.muted())

                with ui.row().classes('items-center gap-3'):
                    theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
                    theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
                    binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')

            ui.separator()

            with ui.row().classes('w-full gap-5 items-stretch no-wrap'):
                # ── Sidebar ───────────────────────────────────────────────────
                with ui.column().classes('gap-4 py-2 w-80 min-w-80'):
                    ui.label('Connection').classes('font-bold text-lg')

                    # Status / discovery feedback
                    status_label = ui.label('Connecting…').classes(theme.muted() + ' text-sm')

                    # Auto-discovered summary (shown when params were pulled from config store)
                    with ui.column().classes('gap-1 w-full') as connection_summary:
                        connection_summary.set_visibility(False)
                        ui.label('Auto-discovered params:').classes('text-xs font-semibold ' + theme.muted())
                        with ui.column().classes('gap-0 pl-2'):
                            # Labels are filled in by load_connection via _populate_form
                            pass
                        edit_btn = ui.button('Edit connection', icon='edit', on_click=lambda: (
                            connection_summary.set_visibility(False),
                            connection_form.set_visibility(True),
                        )).props('flat dense color="primary"').classes('self-start mt-1')

                    # Manual / editable form
                    with ui.column().classes('gap-2 w-full') as connection_form:
                        connection_form.set_visibility(False)
                        host_input = ui.input('Host', value='127.0.0.1').props('outlined dense').classes('w-full')
                        port_input = ui.input('Port', value='5432').props('outlined dense').classes('w-full')
                        dbname_input = ui.input('Database', value='test_historian').props('outlined dense').classes('w-full')
                        user_input = ui.input('User', value='historian').props('outlined dense').classes('w-full')
                        password_input = ui.input('Password', value='historian').props('outlined dense type=password').classes('w-full')
                        connect_btn = ui.button('Connect', icon='link', on_click=connect_to_db).props('color="primary"').classes('w-full')

                    ui.separator()

                    ui.label('Tables').classes('font-bold text-lg')
                    table_tree = ui.tree(
                        nodes=[],
                        label_key='label',
                        on_select=lambda e: on_table_change(e.value) if e.value in tables else None,
                    ).classes('w-full max-h-96 overflow-y-auto')

                ui.separator().props('vertical')

                # ── Main content ──────────────────────────────────────────────
                with ui.column().classes('gap-4 py-2 flex-grow min-w-0'):
                    with ui.row().classes('w-full items-center gap-3'):
                        table_select = ui.select(
                            options=[],
                            label='Active Table',
                            on_change=lambda e: on_table_change(e.value) if e.value else None,
                        ).props('outlined dense').classes('w-64')

                        ui.button(icon='refresh', on_click=load_table_data).props('flat round color="primary"').tooltip('Refresh data')
                        ui.button('Export CSV', icon='download', on_click=export_csv).props('outline color="primary"').tooltip('Export current view to CSV')
                        ui.space()
                        pagination_label = ui.label('No table selected').classes('text-sm')

                    grid_container = ui.column().classes('w-full flex-grow')

    # Initial load
    ui.timer(0.1, load_connection, once=True)
