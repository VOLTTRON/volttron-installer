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
    conn_params = {}
    tables = []
    selected_table = None
    table_data = {"columns": [], "rows": [], "total_count": 0}
    limit = 500
    offset = 0

    # ── UI element references ─────────────────────────────────────────────────
    host_input = None
    port_input = None
    dbname_input = None
    user_input = None
    password_input = None
    table_list_container = None
    grid_container = None
    ag_grid = None
    pagination_label = None
    status_label = None
    active_table_label = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def show_loading(message: str = "Loading..."):
        if not grid_container:
            return
        grid_container.clear()
        with grid_container:
            with ui.column().classes('w-full items-center justify-center py-16 gap-4'):
                ui.spinner(size='lg')
                ui.label(message).classes('text-grey-5 text-sm')

    def render_table_list():
        """Re-render the sidebar table list, highlighting the active table."""
        if not table_list_container:
            return
        table_list_container.clear()
        with table_list_container:
            for t in tables:
                is_active = t == selected_table
                row_classes = (
                    'w-full flex items-center gap-2 px-3 py-2 rounded cursor-pointer '
                    + ('bg-primary text-white' if is_active else 'hover:bg-grey-2 dark:hover:bg-grey-8')
                )
                with ui.row().classes(row_classes).on('click', lambda _, name=t: on_table_change(name)):
                    ui.icon('table_chart').classes('text-sm ' + ('text-white' if is_active else 'text-primary'))
                    ui.label(t).classes('text-sm font-medium')

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

    # ── Discovery ─────────────────────────────────────────────────────────────

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
            _populate_form(conn_params)
            if status_label:
                status_label.text = f"Auto-discovered from agent: {identity}"
            await connect_to_db()
        else:
            conn_params = dict(_DEFAULT_PARAMS)
            _populate_form(conn_params)
            if status_label:
                status_label.text = "Enter connection details and click Connect."

    # ── Connect / table loading ───────────────────────────────────────────────

    async def connect_to_db():
        nonlocal tables, selected_table, conn_params
        conn_params = _params_from_form()
        selected_table = None
        tables = []
        render_table_list()
        if active_table_label:
            active_table_label.text = "No table selected"
        show_loading("Connecting to database…")

        try:
            tables = await postgresql_historian.list_tables(conn_params)
            render_table_list()

            if tables:
                default_table = next((t for t in tables if t.lower() in ["data", "topics"]), tables[0])
                await on_table_change(default_table)
            else:
                if grid_container:
                    grid_container.clear()
                ui.notify("Connected — no tables found in public schema.", type="warning")
        except Exception as e:
            if grid_container:
                grid_container.clear()
            ui.notify(f"Connection failed: {e}", type="negative")

    async def on_table_change(table_name: str):
        nonlocal selected_table, offset
        if not table_name:
            return
        selected_table = table_name
        offset = 0
        render_table_list()
        if active_table_label:
            active_table_label.text = table_name
        await load_table_data()

    async def load_table_data():
        nonlocal table_data
        if not conn_params or not selected_table:
            return
        show_loading(f"Loading {selected_table}…")
        try:
            table_data = await postgresql_historian.query_table(
                conn_params, selected_table, limit=limit, offset=offset
            )
            total_count = table_data["total_count"]
            if pagination_label:
                pagination_label.text = f"Total: {total_count} rows"
            update_grid()
        except Exception as e:
            if grid_container:
                grid_container.clear()
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

                    status_label = ui.label('Connecting…').classes(theme.muted() + ' text-sm')

                    with ui.column().classes('gap-2 w-full'):
                        host_input = ui.input('Host', value='127.0.0.1').props('outlined dense').classes('w-full')
                        port_input = ui.input('Port', value='5432').props('outlined dense').classes('w-full')
                        dbname_input = ui.input('Database', value='test_historian').props('outlined dense').classes('w-full')
                        user_input = ui.input('User', value='historian').props('outlined dense').classes('w-full')
                        password_input = ui.input('Password', value='historian').props('outlined dense type=password').classes('w-full')
                        ui.button('Connect', icon='link', on_click=connect_to_db).props('color="primary"').classes('w-full')

                    ui.separator()

                    ui.label('Tables').classes('font-bold text-lg')
                    table_list_container = ui.column().classes('w-full gap-1 max-h-96 overflow-y-auto')

                ui.separator().props('vertical')

                # ── Main content ──────────────────────────────────────────────
                with ui.column().classes('gap-4 py-2 flex-grow min-w-0'):
                    with ui.row().classes('w-full items-center gap-3'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('table_chart').classes('text-primary')
                            active_table_label = ui.label('No table selected').classes('font-bold text-base')

                        ui.button(icon='refresh', on_click=load_table_data).props('flat round color="primary"').tooltip('Refresh data')
                        ui.button('Export CSV', icon='download', on_click=export_csv).props('outline color="primary"').tooltip('Export current view to CSV')
                        ui.space()
                        pagination_label = ui.label('').classes('text-sm')

                    grid_container = ui.column().classes('w-full flex-grow')

    # Initial load
    ui.timer(0.1, load_connection, once=True)
