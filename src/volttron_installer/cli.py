import argparse
import os

from nicegui import ui

import volttron_installer.app  # registers all @ui.page routes and mounts as a side effect
from volttron_installer.app import ASSETS_DIR, ssl_options


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='volttron-installer',
        description='VOLTTRON Installer web UI',
    )
    p.add_argument('--host', default='0.0.0.0', help='Bind address (default: 0.0.0.0)')
    p.add_argument('--port', type=int, default=8080, help='Port to listen on (default: 8080)')
    p.add_argument('--ssl-cert', metavar='PATH', help='PEM certificate file for HTTPS')
    p.add_argument('--ssl-key', metavar='PATH', help='PEM private key file for HTTPS')
    p.add_argument('--ssl-key-password', metavar='PASSWORD', help='Password for encrypted private key')
    p.add_argument('--storage-secret', metavar='SECRET', help='NiceGUI session storage secret')
    p.add_argument('--data-dir', metavar='PATH', help='Directory for runtime data (instances, Ansible configs)')
    p.add_argument('--show', dest='show', action='store_true', help='Open a browser window on startup')
    p.add_argument('--no-show', dest='show', action='store_false', help='Do not open a browser window (default)')
    p.set_defaults(show=False)
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)

    if args.data_dir:
        os.environ['VOLTTRON_INSTALLER_DATA_DIR'] = args.data_dir

    ssl = ssl_options(
        certfile=args.ssl_cert,
        keyfile=args.ssl_key,
        keyfile_password=args.ssl_key_password,
    )

    storage_secret = (
        args.storage_secret
        or os.environ.get('VOLTTRON_INSTALLER_STORAGE_SECRET', 'volttron-installer-secret')
    )

    ui.run(
        title='VOLTTRON Installer',
        dark=False,
        show=args.show,
        favicon=str(ASSETS_DIR / 'favicon.ico'),
        reload=False,
        host=args.host,
        port=args.port,
        storage_secret=storage_secret,
        **ssl,
    )
