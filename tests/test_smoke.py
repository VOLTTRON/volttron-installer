import os
import pytest
from pathlib import Path


def test_package_importable():
    import volttron_installer
    assert hasattr(volttron_installer, '__version__')
    assert volttron_installer.__version__ == '0.1.0rc0'


def test_cli_parser():
    from volttron_installer.cli import build_parser
    args = build_parser().parse_args(['--port', '9000', '--no-show'])
    assert args.port == 9000
    assert args.show is False


def test_cli_parser_defaults():
    from volttron_installer.cli import build_parser
    args = build_parser().parse_args([])
    assert args.host == '0.0.0.0'
    assert args.port == 8080
    assert args.show is False
    assert args.ssl_cert is None
    assert args.ssl_key is None


def test_ssl_options_empty_when_unset(monkeypatch):
    monkeypatch.delenv('VOLTTRON_INSTALLER_SSL_CERTFILE', raising=False)
    monkeypatch.delenv('VOLTTRON_INSTALLER_SSL_KEYFILE', raising=False)
    monkeypatch.delenv('VOLTTRON_INSTALLER_SSL_KEYFILE_PASSWORD', raising=False)
    from volttron_installer.app import ssl_options
    assert ssl_options() == {}


def test_ssl_options_raises_when_only_cert_given(tmp_path, monkeypatch):
    monkeypatch.delenv('VOLTTRON_INSTALLER_SSL_CERTFILE', raising=False)
    monkeypatch.delenv('VOLTTRON_INSTALLER_SSL_KEYFILE', raising=False)
    cert = tmp_path / 'server.crt'
    cert.write_text('cert')
    from volttron_installer.app import ssl_options
    with pytest.raises(RuntimeError, match='HTTPS requires both'):
        ssl_options(certfile=str(cert))


def test_assets_dir_contains_favicon():
    from volttron_installer.app import ASSETS_DIR
    assert (Path(ASSETS_DIR) / 'favicon.ico').is_file()
