import os
import pytest
import asyncio
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


def test_logs_page_color_classes():
    from volttron_installer.manage_instances.logs_page import _get_level_class

    assert 'text-red-400' in _get_level_class('2026-08-05 ERROR [main] something broke')
    assert 'text-red-400' in _get_level_class('CRITICAL crash')
    assert 'text-amber-400' in _get_level_class('WARNING database disk image is malformed')
    assert 'text-amber-400' in _get_level_class('WARN legacy syntax')
    assert 'text-sky-400' in _get_level_class('DEBUG checking peer')
    assert 'text-emerald-400' in _get_level_class('INFO platform started')
    assert 'text-slate-300' in _get_level_class('non-level string')


def test_vui_log_helpers_use_discovery_and_bounded_tail(monkeypatch):
    from volttron_installer.manage_instances import agent_management

    calls = []

    async def fake_call(instance, path, params=None):
        calls.append((instance, path, params))
        if not path:
            return {'logs': [{'id': 'volttron.log'}, {'id': 'volttron.log.1'}], 'retention': None}
        return {'log_id': 'volttron.log.1', 'lines': ['latest entry']}

    monkeypatch.setattr(agent_management, '_call_vui_logs', fake_call)
    instance = {'name': 'test-platform'}

    assert asyncio.run(agent_management.list_logs(instance)) == [
        {'id': 'volttron.log'}, {'id': 'volttron.log.1'},
    ]
    assert asyncio.run(agent_management.read_log_tail(instance, 'volttron.log.1', 20000)) == {
        'log_id': 'volttron.log.1',
        'lines': ['latest entry'],
    }
    assert calls == [
        (instance, '', None),
        (instance, 'volttron.log.1', {'tail': 10000, 'bytes': 65536}),
    ]


def test_logs_page_simplified_api():
    from volttron_installer.manage_instances import logs_page

    # Verify pagination functions have been removed
    assert not hasattr(logs_page, 'load_older')
    assert not hasattr(logs_page, 'load_newer')
    # Verify render exists and takes 1 argument
    assert hasattr(logs_page, 'render')
    import inspect
    sig = inspect.signature(logs_page.render)
    assert 'instance_name' in sig.parameters



