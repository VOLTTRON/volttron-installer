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
<meta name="color-scheme" content="dark light">
<script>
(function () {
  const theme = localStorage.getItem('volttron-theme') || 'dark';
  document.documentElement.dataset.theme = theme;
})();
</script>
<style>
:root {
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
  --segmented-bg: rgba(255, 255, 255, 0.06);
  --segmented-border: rgba(255, 255, 255, 0.16);
  --segmented-hover: rgba(255, 255, 255, 0.08);
  --segmented-active-bg: linear-gradient(135deg, #6366f1, #8b5cf6);
  --segmented-active-shadow: 0 8px 22px rgba(99, 102, 241, 0.32);
}

html[data-theme="light"],
body.body--light {
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
  --segmented-bg: rgba(17, 24, 39, 0.04);
  --segmented-border: rgba(17, 24, 39, 0.14);
  --segmented-hover: rgba(99, 102, 241, 0.08);
  --segmented-active-bg: linear-gradient(135deg, #4f46e5, #7c3aed);
  --segmented-active-shadow: 0 8px 18px rgba(79, 70, 229, 0.22);
}

html,
body,
#app,
.nicegui-content,
.q-layout,
.q-page-container,
.q-page {
  background-color: var(--bg-color);
  color: var(--text-color);
}

html {
  background-color: var(--bg-color);
}

body {
  font-family: "Inter", sans-serif;
  min-height: 100vh;
  transition: color 0.18s ease;
}

body.body--dark {
  color-scheme: dark;
}

body.body--light {
  color-scheme: light;
}

.q-layout,
.q-page-container,
.q-page,
.nicegui-content {
  min-height: 100vh;
  transition: background-color 0.18s ease, color 0.18s ease;
}

.volttron-segmented {
  background: var(--segmented-bg);
  border: 1px solid var(--segmented-border);
  border-radius: 10px;
  padding: 4px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.volttron-segmented .q-btn {
  min-height: 38px;
  border-radius: 7px;
  color: var(--text-muted);
  font-weight: 700;
  letter-spacing: 0;
  transition: background 0.16s ease, color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.volttron-segmented .q-btn:not([aria-pressed="true"]):hover {
  background: var(--segmented-hover);
  color: var(--text-color);
}

.volttron-segmented .q-btn[aria-pressed="true"],
.volttron-segmented .q-btn.q-btn--active {
  background: var(--segmented-active-bg);
  color: #ffffff;
  box-shadow: var(--segmented-active-shadow);
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
    ui.run(title='VOLTTRON Installer', dark=True, show=False, favicon='assets/favicon.ico', reload=False)
