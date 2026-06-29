from nicegui import ui
from volttron_installer.manage_instances.historian_viewers import sqlite_viewer_page, postgresql_viewer_page


def show_page(instance_name: str):
    with ui.tabs().classes('w-full') as tabs:
        sqlite_tab = ui.tab('SQLite', icon='storage')
        pg_tab = ui.tab('PostgreSQL', icon='dns')

    with ui.tab_panels(tabs, value=sqlite_tab).classes('w-full'):
        with ui.tab_panel(sqlite_tab):
            sqlite_viewer_page.show_page(instance_name)
        with ui.tab_panel(pg_tab):
            postgresql_viewer_page.show_page(instance_name)
