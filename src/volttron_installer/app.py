import os
from pathlib import Path

from nicegui import ui, app
import src.home as home
import src.deploy_platforms.deploy_platform_ui as deploy_platform
import src.manage_instances.instances as instances
import src.manage_instances.manage_main as manage_main
import src.manage_instances.config_store_page as config_store_page
import src.manage_instances.historian_viewers.historian_viewer_page as historian_viewer_page
import src.bacnet_scan.bacnet_scan_ui as bacnet_scan_ui
from bacnet_scan_api.main import app as bacnet_app

app.mount('/bacnet_api', bacnet_app)
app.add_static_files('/assets', 'assets')


PAGE_HEAD = '''
<link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
'''


def ssl_options() -> dict[str, str]:
    certfile = os.environ.get('VOLTTRON_INSTALLER_SSL_CERTFILE', '').strip()
    keyfile = os.environ.get('VOLTTRON_INSTALLER_SSL_KEYFILE', '').strip()
    keyfile_password = os.environ.get('VOLTTRON_INSTALLER_SSL_KEYFILE_PASSWORD', '').strip()

    if not certfile and not keyfile:
        return {}
    if not certfile or not keyfile:
        raise RuntimeError(
            'HTTPS requires both VOLTTRON_INSTALLER_SSL_CERTFILE and '
            'VOLTTRON_INSTALLER_SSL_KEYFILE.'
        )

    cert_path = Path(certfile).expanduser()
    key_path = Path(keyfile).expanduser()
    if not cert_path.is_file():
        raise RuntimeError(f'HTTPS certificate file does not exist: {cert_path}')
    if not key_path.is_file():
        raise RuntimeError(f'HTTPS key file does not exist: {key_path}')

    options = {
        'ssl_certfile': str(cert_path),
        'ssl_keyfile': str(key_path),
    }
    if keyfile_password:
        options['ssl_keyfile_password'] = keyfile_password
    return options


@ui.page('/')
def home_page():
    ui.add_head_html(PAGE_HEAD)
    home.render()

@ui.page('/deploy')
def deploy_page():
    ui.add_head_html(PAGE_HEAD)
    deploy_platform.render()

@ui.page('/deploy/copy/{instance_name}')
def copy_deploy_page(instance_name: str):
    ui.add_head_html(PAGE_HEAD)
    deploy_platform.render(copy_from=instance_name)

@ui.page('/instances')
def instances_page():
    ui.add_head_html(PAGE_HEAD)
    instances.render()

@ui.page('/manage/{instance_name}/config-store/{agent_identity}')
def config_store(instance_name: str, agent_identity: str):
    ui.add_head_html(PAGE_HEAD)
    config_store_page.render(instance_name, agent_identity)

@ui.page('/manage/{instance_name}/historian')
def historian_viewer(instance_name: str):
    ui.add_head_html(PAGE_HEAD)
    historian_viewer_page.show_page(instance_name)

@ui.page('/manage/{instance_name}')
def manage_page(instance_name: str):
    ui.add_head_html(PAGE_HEAD)
    manage_main.render(instance_name)

@ui.page('/bacnet_scan')
def bacnet_scan_page():
    ui.add_head_html(PAGE_HEAD)
    bacnet_scan_ui.render()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title='VOLTTRON Installer',
        dark=False,
        show=False,
        favicon='assets/favicon.ico',
        reload=False,
        storage_secret=os.environ.get('VOLTTRON_INSTALLER_STORAGE_SECRET', 'volttron-installer-secret'),
        **ssl_options(),
    )
