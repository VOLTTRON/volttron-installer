from nicegui import ui, binding
import random
import string
import asyncio
import subprocess
from urllib.parse import urlparse, urlunparse

import src.db as db
from src import theme

def generate_instance_name():
    return 'volttron-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

def _next_vip_address(source_address: str) -> str:
    used_ports = set()
    for instance in db.get_instances():
        parsed = urlparse(instance.get('vip') or '')
        if parsed.port:
            used_ports.add(parsed.port)
        elif instance.get('is_local', True):
            used_ports.add(22916)

    parsed = urlparse(source_address or 'tcp://127.0.0.1:22916')
    port = parsed.port or 22916
    while port in used_ports:
        port += 1
    return urlunparse((parsed.scheme or 'tcp', f'{parsed.hostname or "127.0.0.1"}:{port}', '', '', '', ''))


def _remote_listen_address(address: str) -> str:
    parsed = urlparse(address)
    if parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        return address
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    return urlunparse((parsed.scheme or 'http', f'0.0.0.0:{port}', parsed.path or '', '', '', ''))


def _copy_defaults(copy_from: str | None) -> tuple[dict, dict | None]:
    instances = db.get_instances()
    used_names = {instance.get('name') for instance in instances}
    default_name = generate_instance_name()
    while default_name in used_names:
        default_name = generate_instance_name()
    source = next((instance for instance in instances if instance.get('name') == copy_from), None)
    defaults = {
        'name': default_name,
        'type': 'Modular',
        'is_local': True,
        'host': '',
        'ssh_username': '',
        'ssh_port': '22',
        'ssh_key_path': '~/.ssh/volttron_installer',
        'ssh_ignore_host_keys': False,
        'vip': _next_vip_address(''),
        'volttron_home': f'~/.{default_name}',
        'venv': f'~/.{default_name}.venv',
        'web_enabled': True,
        'web_bind_address': 'http://127.0.0.1:8443',
        'web_ssl_cert': '',
        'web_ssl_key': '',
        'package_source': 'Automatic',
        'http_proxy': '',
        'https_proxy': '',
        'python_interpreter': 'auto',
        'manual_core_package': '',
        'manual_auth_package': '',
        'manual_zmq_package': '',
        'manual_tree_package': '',
        'manual_web_package': '',
    }
    if not source:
        return defaults, None

    defaults.update({
        'type': source.get('type') or 'Modular',
        'is_local': source.get('is_local', True),
        'host': '' if source.get('is_local', True) else source.get('host', ''),
        'ssh_username': source.get('ssh_username', ''),
        'ssh_port': str(source.get('ssh_port') or '22'),
        'ssh_key_path': source.get('ssh_key_path') or '~/.ssh/volttron_installer',
        'ssh_ignore_host_keys': bool(source.get('ssh_ignore_host_keys')),
        'vip': _next_vip_address(source.get('vip', '')),
        'web_enabled': source.get('web_enabled', bool(source.get('web_bind_address'))),
        'web_bind_address': source.get('web_listen_address') or source.get('web_bind_address') or defaults['web_bind_address'],
        'web_ssl_cert': source.get('web_ssl_cert', ''),
        'web_ssl_key': source.get('web_ssl_key', ''),
        'package_source': source.get('package_source', 'Automatic'),
        'http_proxy': source.get('http_proxy', ''),
        'https_proxy': source.get('https_proxy', ''),
        'python_interpreter': source.get('python_interpreter', 'auto'),
        'manual_core_package': source.get('manual_core_package', ''),
        'manual_auth_package': source.get('manual_auth_package', ''),
        'manual_zmq_package': source.get('manual_zmq_package', ''),
        'manual_tree_package': source.get('manual_tree_package', ''),
        'manual_web_package': source.get('manual_web_package', ''),
    })
    return defaults, source


def render(copy_from: str | None = None):
    dark_mode = theme.dark_mode()
    defaults, source_instance = _copy_defaults(copy_from)
    default_name = defaults['name']

    async def perform_install():
        is_local_install = install_target_toggle.value == 'Local'
        install_target = 'local' if is_local_install else 'remote'
        ui.notify(f'Starting {install_target} installation...', type='info')
        
        with ui.dialog() as dialog, ui.card().classes('p-8 items-center gap-4'):
            ui.label('Deploying Platform').classes('text-xl font-bold')
            ui.spinner(size='lg')
            status_label = ui.label('Initializing...')
        dialog.open()
        
        from src.deploy_platforms.port_allocator import allocate_remote_web_bind_address, allocate_web_bind_address
        
        try:
            ssh_instance = None
            if not is_local_install:
                if not (host_input.value or '').strip():
                    raise Exception('Remote host is required.')
                if not (username_input.value or '').strip():
                    raise Exception('SSH username is required.')

                temp_password = temporary_password_input.value or ''
                sudo_setup_password = sudo_password_input.value or temp_password
                key_path = (key_path_input.value or '~/.ssh/volttron_installer').strip()
                ssh_instance = {
                    'host': (host_input.value or '').strip(),
                    'ssh_username': (username_input.value or '').strip(),
                    'ssh_port': ssh_port_input.value or '22',
                    'ssh_key_path': key_path,
                    'ssh_ignore_host_keys': bool(ignore_host_keys_checkbox.value),
                    'is_local': False,
                }
                password_instance = {
                    **ssh_instance,
                    'ssh_key_path': '',
                    'ssh_password': temp_password,
                }
                sudo_instance = {
                    **ssh_instance,
                    'ssh_password': sudo_setup_password,
                }
                from src import ssh_remote
                status_label.set_text('Testing SSH key access...')
                try:
                    await ssh_remote.test_connection(ssh_instance)
                except Exception:
                    if not temp_password:
                        raise Exception(
                            'SSH key access failed. Enter the temporary remote password so the installer can '
                            'install its public key, or add the public key manually.'
                        )
                    status_label.set_text('Installing SSH key with temporary password...')
                    private_key_path, public_key = ssh_remote.ensure_local_key_pair(key_path)
                    await ssh_remote.install_public_key(password_instance, public_key)
                    ssh_instance['ssh_key_path'] = private_key_path
                    status_label.set_text('Re-testing SSH key access...')
                    await ssh_remote.test_connection(ssh_instance)

                status_label.set_text('Checking sudo access...')
                try:
                    await ssh_remote.run(ssh_instance, 'sudo -n true', timeout=30)
                except Exception:
                    if not sudo_setup_password:
                        raise Exception(
                            'Remote sudo requires a password. Enter the temporary remote password so the '
                            'installer can configure non-interactive sudo for Ansible, or configure '
                            'passwordless sudo manually.'
                        )
                    status_label.set_text('Configuring non-interactive sudo...')
                    await ssh_remote.ensure_passwordless_sudo(sudo_instance)
                    await ssh_remote.run(ssh_instance, 'sudo -n true', timeout=30)
            else:
                status_label.set_text('Checking local sudo access...')
                sudo_check = await asyncio.to_thread(
                    subprocess.run,
                    ['sudo', '-n', 'true'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if sudo_check.returncode != 0 and not (sudo_password_input.value or ''):
                    raise Exception(
                        'Local deployment needs sudo for Ubuntu package setup and systemd service management. '
                        'Enter your sudo password in Advanced Settings; it is used only for this deployment and is not saved.'
                    )

            venv_path = venv_input.value if venv_input.value else '~/volttron.venv'
            volttron_home = volttron_home_input.value if volttron_home_input.value else '~/.volttron'
            host = 'localhost' if is_local_install else host_input.value
            web_bind_address = web_bind_address_input.value or (
                "http://127.0.0.1:8443" if is_local_install else "http://0.0.0.0:8443"
            )
            if not is_local_install:
                web_bind_address = _remote_listen_address(web_bind_address)
            port_messages = []
            if web_interface_toggle.value:
                if is_local_install:
                    web_bind_address, port_messages = allocate_web_bind_address(
                        web_bind_address,
                        host,
                        can_probe_socket=True,
                    )
                else:
                    from src import ssh_remote
                    web_bind_address, port_messages = await allocate_remote_web_bind_address(
                        web_bind_address,
                        host,
                        lambda bind_host, port: ssh_remote.is_tcp_port_bound(ssh_instance, bind_host, port),
                    )
                for message in port_messages:
                    ui.notify(message, type='warning')
                if port_messages:
                    status_label.set_text(port_messages[-1])
                    await asyncio.sleep(1.5)

            extra_packages = []
            if package_source.value == 'Manual':
                extra_packages = []
                if core_pkg_input.value:
                    extra_packages.append(f"git+https://github.com/{core_pkg_input.value}")
                extra_packages.extend([
                    "pyzmq>=25.1.2,<26.0.0",
                    "msgpack-python>=0.5.6,<0.6.0",
                    "treelib>=1.6.1",
                    "pydantic>=2.0.0,<3.0.0"
                ])
                if web_interface_toggle.value:
                    extra_packages.extend([
                        "argon2-cffi>=21.3.0,<22.0.0",
                        "jinja2>=2.10.1",
                        "passlib>=1.7.4,<2.0.0",
                        "PyJWT==1.7.1",
                        "requests>=2.28.1",
                        "werkzeug>=2.1.2",
                        "ws4py>=0.5.1"
                    ])
                if auth_pkg_input.value:
                    extra_packages.append(f"git+https://github.com/{auth_pkg_input.value}")
                if zmq_pkg_input.value:
                    extra_packages.append(f"git+https://github.com/{zmq_pkg_input.value}")
                if web_interface_toggle.value:
                    if tree_pkg_input.value:
                        extra_packages.append(f"git+https://github.com/{tree_pkg_input.value}")
                    else:
                        extra_packages.append('volttron-lib-tree')
                        
                    if web_pkg_input.value:
                        extra_packages.append(f"git+https://github.com/{web_pkg_input.value}")

            status_label.set_text('Running Ansible deployment...')
            ssl_cert = (web_ssl_cert_input.value or '').strip()
            ssl_key = (web_ssl_key_input.value or '').strip()
            from src.deploy_platforms.ansible_deploy import deploy_with_ansible
            ansible_result = await deploy_with_ansible(
                instance_name=instance_name_input.value,
                is_local=is_local_install,
                host=host,
                username=(username_input.value or '').strip() if not is_local_install else '',
                ssh_port=ssh_port_input.value or '22',
                ssh_key_path=(key_path_input.value or '').strip() if not is_local_install else '',
                ignore_host_keys=bool(ignore_host_keys_checkbox.value),
                volttron_home=volttron_home,
                volttron_venv=venv_path,
                web_enabled=web_interface_toggle.value,
                web_bind_address=web_bind_address,
                web_ssl_cert=ssl_cert,
                web_ssl_key=ssl_key,
                extra_packages=extra_packages,
                become_password=sudo_password_input.value or temporary_password_input.value or '',
                http_proxy=http_proxy_input.value or '',
                https_proxy=https_proxy_input.value or '',
                python_interpreter=python_path_input.value or 'auto',
            )
            web_creds = ansible_result.web_credentials
            
            dialog.close()
            
            instance_data = {
                'name': instance_name_input.value,
                'type': type_toggle.value,
                'host': host,
                'is_local': is_local_install,
                'vip': vip_input.value,
                'venv': venv_path,
                'volttron_home': volttron_home,
                'deployment_method': 'ansible',
                'systemd_service': f'volttron-{instance_name_input.value}.service',
                'ansible_inventory': str(ansible_result.inventory_path),
                'ansible_host_alias': ansible_result.host_alias,
                'web_enabled': bool(web_interface_toggle.value),
                'web_ssl_cert': ssl_cert,
                'web_ssl_key': ssl_key,
                'package_source': package_source.value,
                'http_proxy': http_proxy_input.value or '',
                'https_proxy': https_proxy_input.value or '',
                'python_interpreter': python_path_input.value or 'auto',
                'manual_core_package': core_pkg_input.value or '',
                'manual_auth_package': auth_pkg_input.value or '',
                'manual_zmq_package': zmq_pkg_input.value or '',
                'manual_tree_package': tree_pkg_input.value or '',
                'manual_web_package': web_pkg_input.value or '',
            }
            if not is_local_install:
                instance_data.update({
                    'ssh_username': ssh_instance['ssh_username'],
                    'ssh_port': ssh_instance['ssh_port'],
                    'ssh_key_path': ssh_instance.get('ssh_key_path', ''),
                    'ssh_ignore_host_keys': ssh_instance.get('ssh_ignore_host_keys', False),
                    'ssh_auth_method': 'Key',
                })
            # Merge web credentials
            instance_data.update(web_creds)
            
            db.save_instance(instance_data)
            
            ui.notify('Platform successfully installed!', type='positive')
            ui.navigate.to('/instances')
        except Exception as e:
            dialog.close()
            ui.notify(f"Installation failed: {str(e)}", type='negative')

    with ui.column().classes(theme.page_container('py-10 px-4')):
        # Header
        with ui.row().classes('w-full max-w-4xl justify-between items-center mb-8'):
            with ui.row().classes('items-center gap-4'):
                back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round')
                binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                ui.label('Copy Platform' if source_instance else 'New Platform').classes(theme.title())
            
            with ui.row().classes('items-center gap-2'):
                theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
                theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
                binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')
                ui.button('Help', icon='help_outline').props('flat color="gray"')
        
        # Main Form Container
        with ui.column().classes('w-full max-w-4xl gap-8'):
            
            # Connection Section
            with ui.card().classes(theme.card('p-8')):
                with ui.row().classes('items-center gap-3 mb-6'):
                    ui.icon('lan', size='md', color='primary')
                    ui.label('Connection').classes('text-2xl font-semibold')
                
                with ui.column().classes('w-full gap-5'):
                    with ui.column().classes('w-full gap-2'):
                        ui.label('Install Target').classes(theme.small_muted('font-medium'))
                        
                        def handle_install_target_change(e):
                            try:
                                if e.value == 'Remote':
                                    if web_bind_address_input.value == 'http://127.0.0.1:8443':
                                        web_bind_address_input.value = 'http://0.0.0.0:8443'
                                else:
                                    if web_bind_address_input.value == 'http://0.0.0.0:8443':
                                        web_bind_address_input.value = 'http://127.0.0.1:8443'
                            except NameError:
                                pass
                                
                        install_target_toggle = ui.toggle(['Local', 'Remote'], value='Local' if defaults['is_local'] else 'Remote', on_change=handle_install_target_change).props('unelevated no-caps spread toggle-color="primary" text-color="grey-7"').classes('w-full')
                    
                    with ui.row().classes('w-full gap-4').bind_visibility_from(install_target_toggle, 'value', backward=lambda v: v == 'Remote'):
                        host_input = ui.input('Host', value=defaults['host']).props('outlined rounded color="primary"').classes('flex-grow')
                        username_input = ui.input('Username', value=defaults['ssh_username']).props('outlined rounded color="primary"').classes('flex-grow')
                        ssh_port_input = ui.input('SSH Port', value=defaults['ssh_port']).props('outlined rounded color="primary"').classes('w-24')

                    with ui.column().classes('w-full gap-3').bind_visibility_from(install_target_toggle, 'value', backward=lambda v: v == 'Remote'):
                        ui.label('SSH Authentication').classes(theme.small_muted('font-medium'))
                        key_path_input = ui.input('Private Key Path', value=defaults['ssh_key_path']).props('outlined rounded color="primary"').classes('w-full')
                        temporary_password_input = ui.input('Temporary SSH/Sudo Password', password=True, password_toggle_button=True).props('outlined rounded color="primary" autocomplete="current-password"').classes('w-full')
                        ui.label('Used only during this deployment to install the SSH key on a fresh host and, if needed, configure non-interactive sudo for apt and systemd. It is not saved.').classes(theme.small_muted())
                        ui.label('After setup, deployment continues with key-based SSH and passwordless sudo. Leave blank when both are already configured.').classes(theme.small_muted())
                        with ui.expansion('How to create an SSH key', icon='key').classes('w-full').props('header-class="text-muted"'):
                            with ui.column().classes('w-full gap-2 p-4 rounded border'):
                                ui.label('Run these commands on the machine running this installer:').classes(theme.small_muted())
                                ui.code(
                                    'ssh-keygen -t ed25519 -f ~/.ssh/volttron_installer -C volttron-installer\n'
                                    'ssh-copy-id -i ~/.ssh/volttron_installer.pub USER@REMOTE_HOST\n'
                                    'ssh -i ~/.ssh/volttron_installer USER@REMOTE_HOST',
                                    language='bash',
                                ).classes('w-full')
                                ui.label('After the test SSH command works, use ~/.ssh/volttron_installer as the private key path above.').classes(theme.small_muted())
                    
                    with ui.expansion('Advanced Settings', icon='settings').classes('w-full').props('header-class="text-muted"'):
                         with ui.column().classes('w-full gap-4 p-4'):
                            with ui.row().classes('w-full gap-4'):
                                http_proxy_input = ui.input('HTTP Proxy', value=defaults['http_proxy']).props('outlined dense color="primary"').classes('flex-grow')
                                https_proxy_input = ui.input('HTTPS Proxy', value=defaults['https_proxy']).props('outlined dense color="primary"').classes('flex-grow')
                            with ui.row().classes('w-full gap-4'):
                                volttron_home_input = ui.input('VOLTTRON Home', value=defaults['volttron_home']).props('outlined dense color="primary"').classes('flex-grow')
                                venv_input = ui.input('VOLTTRON venv', value=defaults['venv']).props('outlined dense color="primary"').classes('flex-grow')
                            python_path_input = ui.input('VOLTTRON Python Override', value=defaults['python_interpreter']).props('outlined dense color="primary"').classes('w-full')
                            ui.label('Leave auto unless debugging. Auto uses the installer runtime for local Ansible control and creates the VOLTTRON venv with Python 3.10 when needed. This field never changes Ansible’s control Python.').classes(theme.small_muted())
                            sudo_password_input = ui.input('Sudo Password', password=True, password_toggle_button=True).props('outlined dense color="primary" autocomplete="current-password"').classes('w-full')
                            ui.label('Optional. Used for local system package/service setup, or when remote sudo uses a different password than SSH. This is not saved.').classes(theme.small_muted())
                            ignore_host_keys_checkbox = ui.checkbox('Ignore Host Keys (StrictHostKeyChecking=no)', value=defaults['ssh_ignore_host_keys']).props('color="primary"')
 
            # Instance Configuration Section
            with ui.card().classes(theme.card('p-8')):
                with ui.row().classes('items-center gap-3 mb-6'):
                    ui.icon('tune', size='md', color='secondary')
                    ui.label('Instance Configuration').classes('text-2xl font-semibold')
                
                with ui.column().classes('w-full gap-6'):
                    def update_paths(e):
                        volttron_home_input.value = f'~/.{e.value}'
                        venv_input.value = f'~/.{e.value}.venv'

                    def handle_type_change(e):
                        if e.value == 'Monolithic':
                            ui.notify('Monolithic deployments are not implemented yet.', type='warning')
                            type_toggle.value = 'Modular'
                        
                    instance_name_input = ui.input('Instance Name', value=default_name, on_change=update_paths).props('outlined rounded color="primary"').classes('w-full')
                    
                    with ui.column().classes('w-full gap-2'):
                        ui.label('VOLTTRON Type').classes(theme.small_muted('font-medium'))
                        type_toggle = ui.toggle(['Modular', 'Monolithic'], value=defaults['type'], on_change=handle_type_change).props('unelevated no-caps spread toggle-color="primary" text-color="grey-7"').classes('w-full')
                        ui.label('Modular: Agents are pip packages (recommended). Monolithic: Bundled all-in-one.').classes(theme.small_muted())
                    
                    with ui.column().classes('w-full gap-2'):
                        ui.label('Package Source').classes(theme.small_muted('font-medium'))
                        package_source = ui.toggle(['Automatic', 'Manual'], value=defaults['package_source']).props('unelevated no-caps spread toggle-color="primary" text-color="grey-7"').classes('w-full')
                        
                        with ui.column().classes('w-full gap-4 p-4 border rounded-lg mt-2').bind_visibility_from(package_source, 'value', backward=lambda v: v == 'Manual'):
                            ui.label('Manual Package Overrides').classes('font-semibold text-sm')
                            core_pkg_input = ui.input('Core Package', value=defaults['manual_core_package'], placeholder='eclipse-volttron/volttron-core@main').props('outlined dense color="primary"').classes('w-full')
                            auth_pkg_input = ui.input('Auth Package', value=defaults['manual_auth_package'], placeholder='eclipse-volttron/volttron-lib-auth@main').props('outlined dense color="primary"').classes('w-full')
                            zmq_pkg_input = ui.input('ZMQ Package', value=defaults['manual_zmq_package'], placeholder='eclipse-volttron/volttron-lib-zmq@main').props('outlined dense color="primary"').classes('w-full')
                            tree_pkg_input = ui.input('Tree Package', value=defaults['manual_tree_package'], placeholder='eclipse-volttron/volttron-lib-tree@main').props('outlined dense color="primary"').classes('w-full')
                            web_pkg_input = ui.input('Web Package', value=defaults['manual_web_package'], placeholder='eclipse-volttron/volttron-lib-web@main').props('outlined dense color="primary"').classes('w-full')
                    
                    vip_input = ui.input('VIP Address', value=defaults['vip']).props('outlined rounded color="primary"').classes('w-full')
                    
                    with ui.row().classes('w-full justify-between items-center p-4 rounded-xl border'):
                        with ui.column().classes('gap-1'):
                            ui.label('Web Interface').classes('font-semibold')
                            ui.label('Browser-based platform management and monitoring').classes(theme.small_muted())
                        web_interface_toggle = ui.switch(value=defaults['web_enabled']).props('color="primary"')
                    
                    initial_bind = defaults['web_bind_address']
                    if not defaults['is_local'] and initial_bind == 'http://127.0.0.1:8443':
                        initial_bind = 'http://0.0.0.0:8443'
                    web_bind_address_input = ui.input('Web Bind Address', value=initial_bind).props('outlined rounded color="primary"').classes('w-full')

                    with ui.column().classes('w-full gap-3').bind_visibility_from(web_interface_toggle, 'value'):
                        ui.label('Web Interface Encryption (HTTPS)').classes(theme.small_muted('font-medium'))
                        web_ssl_cert_input = ui.input('SSL Certificate Path (on target host)', value=defaults['web_ssl_cert']).props('outlined rounded color="primary"').classes('w-full')
                        web_ssl_key_input = ui.input('SSL Key Path (on target host)', value=defaults['web_ssl_key']).props('outlined rounded color="primary"').classes('w-full')
                        ui.label('Leave blank to use HTTP. When both paths are set, the bind address scheme is automatically switched to https://.').classes(theme.small_muted())
                        with ui.expansion('How to generate a self-signed certificate', icon='lock').classes('w-full').props('header-class="text-muted"'):
                            with ui.column().classes('w-full gap-2 p-4 rounded border'):
                                ui.label('Run this command on the target host to create a self-signed certificate:').classes(theme.small_muted())
                                ui.code(
                                    'openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt \\\n'
                                    '  -sha256 -days 365 -nodes -subj "/CN=localhost"',
                                    language='bash',
                                ).classes('w-full')
                                ui.label('Then enter the full paths to server.crt and server.key above. For production use a certificate signed by a trusted CA.').classes(theme.small_muted())

                    with ui.row().classes('w-full justify-between items-center p-4 rounded-xl border'):
                        with ui.column().classes('gap-1'):
                            ui.label('Federation').classes('font-semibold')
                            ui.label('Connect this platform to a multi-platform VOLTTRON federation').classes(theme.small_muted())
                        ui.switch(value=False).props('color="primary"')
 
            # Pre-Deployment Agents Section
            with ui.card().classes(theme.card('p-8')):
                with ui.row().classes('items-center gap-3 mb-2'):
                    ui.icon('smart_toy', size='md', color='accent')
                    ui.label('Pre-Deployment Agents').classes('text-2xl font-semibold')
                ui.label('Select agents to install during deployment.').classes(theme.muted('mb-6'))
                
                with ui.row().classes('w-full gap-8'):
                    with ui.column().classes('flex-1 gap-3'):
                        ui.label('Available').classes('font-semibold border-b pb-2 w-full')
                        for agent in ['ListenerAgent', 'VCPLogger', 'PlatformAgent']:
                            with ui.row().classes('w-full justify-between items-center p-3 rounded-lg border'):
                                ui.label(agent)
                                ui.button(icon='add').props('flat round dense color="primary"')
                                
                    ui.separator().props('vertical')
                    
                    with ui.column().classes('flex-1 gap-3'):
                        ui.label('Selected').classes('font-semibold border-b pb-2 w-full')
                        with ui.row().classes('w-full justify-center p-6 border border-dashed border-gray-700 rounded-lg'):
                            ui.label('No agents selected').classes(theme.muted('italic'))
 
            # Action Buttons
            with ui.row().classes('w-full justify-end gap-4 mt-4'):
                cancel_btn = ui.button('Cancel', on_click=lambda: ui.navigate.to('/')).props('outline rounded size="lg"')
                binding.bind_from(cancel_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                
                ui.button('Save & Deploy', on_click=perform_install).props('color="positive" rounded size="lg" icon="rocket_launch"')
