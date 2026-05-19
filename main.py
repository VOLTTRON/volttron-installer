from nicegui import ui
import src.home as home
import src.deploy_platforms.deploy_platform_ui as deploy_platform
import src.manage_instances.instances as instances
import src.manage_instances.manage_main as manage_main
import src.bacnet_scan.bacnet_scan_ui as bacnet_scan_ui
from nicegui import app
from bacnet_scan_api.main import app as bacnet_app

app.mount('/bacnet_api', bacnet_app)

@ui.page('/')
def home_page():
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html('<style>body { background-color: #0f0f13; color: #f3f4f6; font-family: "Inter", sans-serif; }</style>')
    home.render()

@ui.page('/deploy')
def deploy_page():
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html('<style>body { background-color: #0f0f13; color: #f3f4f6; font-family: "Inter", sans-serif; }</style>')
    deploy_platform.render()

@ui.page('/instances')
def instances_page():
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html('<style>body { background-color: #0f0f13; color: #f3f4f6; font-family: "Inter", sans-serif; }</style>')
    instances.render()

@ui.page('/manage/{instance_name}')
def manage_page(instance_name: str):
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html('<style>body { background-color: #0f0f13; color: #f3f4f6; font-family: "Inter", sans-serif; }</style>')
    manage_main.render(instance_name)

@ui.page('/bacnet_scan')
def bacnet_scan_page():
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html('<style>body { background-color: #0f0f13; color: #f3f4f6; font-family: "Inter", sans-serif; }</style>')
    bacnet_scan_ui.render()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='VOLTTRON Installer', dark=True, show=False)
