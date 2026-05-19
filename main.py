from nicegui import ui
import src.home as home
import src.deploy_platforms.deploy_platform_ui as deploy_platform
import src.manage_instances.instances as instances
import src.manage_instances.manage_main as manage_main
import src.bacnet_scan.bacnet_scan_ui as bacnet_scan_ui
from nicegui import app
from bacnet_scan_api.main import app as bacnet_app

app.mount('/bacnet_api', bacnet_app)
app.add_static_files('/assets', 'assets')

PAGE_HEAD = '''
<link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
<style>
body {
  background-color: var(--bg-color);
  color: var(--text-color);
  font-family: "Inter", sans-serif;
  transition: background-color 0.3s ease, color 0.3s ease;
}

:root {
  --bg-color: #f9fafb;
  --text-color: #111827;
  --card-bg: rgba(255, 255, 255, 0.85);
  --card-border: rgba(0, 0, 0, 0.08);
  --card-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
  --input-bg: #ffffff;
  --sub-bg: #f3f4f6;
  --text-muted: #6b7280;
  --text-title: #111827;
  --border-color: rgba(0, 0, 0, 0.08);
  --code-bg: #f3f4f6;
  --code-border: #e5e7eb;
  --text-white-or-dark: #1f2937;
  --header-btn-color: #4b5563;
  --dialog-bg: #ffffff;
}

body.body--dark {
  --bg-color: #0f0f13;
  --text-color: #f3f4f6;
  --card-bg: rgba(30, 30, 36, 0.7);
  --card-border: rgba(255, 255, 255, 0.1);
  --card-shadow: 0 10px 30px rgba(0,0,0,0.5);
  --input-bg: #1a1a20;
  --sub-bg: #1a1a20;
  --text-muted: #9ca3af;
  --text-title: #f3f4f6;
  --border-color: rgba(255, 255, 255, 0.1);
  --code-bg: #15151b;
  --code-border: #2b2d35;
  --text-white-or-dark: #f3f4f6;
  --header-btn-color: #ffffff;
  --dialog-bg: #1e1e24;
}
</style>
'''

@ui.page('/')
def home_page():
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html(PAGE_HEAD)
    home.render()

@ui.page('/deploy')
def deploy_page():
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html(PAGE_HEAD)
    deploy_platform.render()

@ui.page('/instances')
def instances_page():
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html(PAGE_HEAD)
    instances.render()

@ui.page('/manage/{instance_name}')
def manage_page(instance_name: str):
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html(PAGE_HEAD)
    manage_main.render(instance_name)

@ui.page('/bacnet_scan')
def bacnet_scan_page():
    ui.colors(primary='#6366f1', secondary='#a855f7', accent='#ec4899', dark='#121212', positive='#10b981')
    ui.add_head_html(PAGE_HEAD)
    bacnet_scan_ui.render()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='VOLTTRON Installer', dark=True, show=False, favicon='assets/favicon.ico')
