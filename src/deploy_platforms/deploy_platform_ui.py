from nicegui import ui, binding
import random
import string
import asyncio

def generate_instance_name():
    return 'volttron-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

def render():
    dark_mode = ui.dark_mode()
    default_name = generate_instance_name()

    async def perform_install():
        install_target = 'local' if is_local.value else 'remote'
        ui.notify(f'Starting {install_target} installation...', type='info')
        
        with ui.dialog() as dialog, ui.card().classes('p-8 items-center gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 12px;'):
            ui.label('Deploying Platform').classes('text-xl font-bold')
            ui.spinner(size='lg')
            status_label = ui.label('Initializing...')
        dialog.open()
        
        import src.db as db
        from src.deploy_platforms.port_allocator import allocate_web_bind_address
        
        try:
            ssh_instance = None
            if not is_local.value:
                if not (host_input.value or '').strip():
                    raise Exception('Remote host is required.')
                if not (username_input.value or '').strip():
                    raise Exception('SSH username is required.')
                if not (key_path_input.value or '').strip():
                    raise Exception('SSH key path is required for remote deployment.')

                ssh_instance = {
                    'host': (host_input.value or '').strip(),
                    'ssh_username': (username_input.value or '').strip(),
                    'ssh_port': ssh_port_input.value or '22',
                    'ssh_key_path': (key_path_input.value or '').strip(),
                    'ssh_ignore_host_keys': bool(ignore_host_keys_checkbox.value),
                    'is_local': False,
                }
                from src import ssh_remote
                status_label.set_text('Connecting over SSH...')
                await ssh_remote.test_connection(ssh_instance)

            status_label.set_text('Creating virtual environment...')
            # Default to ~/volttron.venv if empty
            venv_path = venv_input.value if venv_input.value else '~/volttron.venv'
            if is_local.value:
                from src.deploy_platforms.create_python_venv import create_venv
                await create_venv(venv_path)
            else:
                from src.deploy_platforms.remote_deploy import create_remote_venv
                await create_remote_venv(ssh_instance, venv_path)
            
            status_label.set_text('Installing VOLTTRON packages...')
            packages_to_install = ['volttron']
            
            if type_toggle.value == 'Modular':
                packages_to_install.extend(['volttron-lib-zmq', 'volttron-lib-auth'])
                if web_interface_toggle.value:
                    packages_to_install.extend(['volttron-lib-tree', 'volttron-lib-web'])
            
            if package_source.value == 'Manual':
                packages_to_install = []
                # First, install the custom core version
                if core_pkg_input.value:
                    packages_to_install.append(f"git+https://github.com/{core_pkg_input.value}")
                
                # Second, install the required 3rd party runtime dependencies natively so pip resolves them correctly
                packages_to_install.extend([
                    "pyzmq>=25.1.2,<26.0.0",
                    "msgpack-python>=0.5.6,<0.6.0",
                    "treelib>=1.6.1",
                    "pydantic>=2.0.0,<3.0.0"
                ])
                if web_interface_toggle.value:
                    packages_to_install.extend([
                        "argon2-cffi>=21.3.0,<22.0.0",
                        "jinja2>=2.10.1",
                        "passlib>=1.7.4,<2.0.0",
                        "PyJWT==1.7.1",
                        "requests>=2.28.1",
                        "werkzeug>=2.1.2",
                        "ws4py>=0.5.1"
                    ])
                    
                # Third, explicitly install the library branches with --no-deps to bypass strict version checks
                if auth_pkg_input.value:
                    packages_to_install.append(f"--no-deps git+https://github.com/{auth_pkg_input.value}")
                if zmq_pkg_input.value:
                    packages_to_install.append(f"--no-deps git+https://github.com/{zmq_pkg_input.value}")
                if web_interface_toggle.value:
                    if tree_pkg_input.value:
                        packages_to_install.append(f"--no-deps git+https://github.com/{tree_pkg_input.value}")
                    else:
                        packages_to_install.append('--no-deps volttron-lib-tree')
                        
                    if web_pkg_input.value:
                        packages_to_install.append(f"--no-deps git+https://github.com/{web_pkg_input.value}")
            
            if is_local.value:
                from src.deploy_platforms.install_volttron_packages import install_packages
                await install_packages(venv_path, packages_to_install)
            else:
                from src.deploy_platforms.remote_deploy import install_remote_packages
                await install_remote_packages(ssh_instance, venv_path, packages_to_install)
            
            status_label.set_text('Configuring VOLTTRON home...')
            volttron_home = volttron_home_input.value if volttron_home_input.value else '~/.volttron'
            host = 'localhost' if is_local.value else host_input.value
            web_bind_address = "http://127.0.0.1:8443" if is_local.value else "http://0.0.0.0:8443"
            port_messages = []
            if web_interface_toggle.value:
                web_bind_address, port_messages = allocate_web_bind_address(
                    web_bind_address,
                    host,
                    can_probe_socket=is_local.value,
                )
                for message in port_messages:
                    ui.notify(message, type='warning')
                if port_messages:
                    status_label.set_text(port_messages[-1])
                    await asyncio.sleep(1.5)
            
            if is_local.value:
                from src.deploy_platforms.configure_volttron import configure_volttron
                web_creds = await configure_volttron(
                    venv_path, 
                    volttron_home, 
                    instance_name_input.value, 
                    web_interface_toggle.value,
                    web_bind_address
                )
            else:
                from src.deploy_platforms.remote_deploy import configure_remote_volttron
                web_creds = await configure_remote_volttron(
                    ssh_instance,
                    venv_path,
                    volttron_home,
                    instance_name_input.value,
                    web_interface_toggle.value,
                    web_bind_address,
                )
            
            dialog.close()
            
            instance_data = {
                'name': instance_name_input.value,
                'type': type_toggle.value,
                'host': host,
                'is_local': is_local.value,
                'vip': vip_input.value,
                'venv': venv_path,
                'volttron_home': volttron_home
            }
            if not is_local.value:
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

    with ui.column().classes('w-full items-center py-10').style('min-height: 100vh;'):
        # Header
        with ui.row().classes('w-full max-w-4xl justify-between items-center mb-8'):
            with ui.row().classes('items-center gap-4'):
                back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round').style('transition: transform 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: translateX(-5px);')).on('mouseleave', lambda e: e.sender.style('transform: translateX(0);'))
                binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                ui.label('New Platform').style('font-size: 2.5rem; font-weight: bold; color: var(--text-color);')
            
            with ui.row().classes('items-center gap-2'):
                theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
                theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
                binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')
                ui.button('Help', icon='help_outline').props('flat color="gray"')
        
        # Main Form Container
        with ui.column().classes('w-full max-w-4xl gap-8'):
            
            # Connection Section
            with ui.card().classes('w-full').style('background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--card-border); border-radius: 16px; padding: 2rem; box-shadow: var(--card-shadow); transition: transform 0.3s ease, border-color 0.3s ease;').on('mouseenter', lambda e: e.sender.style('border-color: rgba(99, 102, 241, 0.5);')).on('mouseleave', lambda e: e.sender.style('border-color: rgba(255, 255, 255, 0.1);')):
                with ui.row().classes('items-center gap-3 mb-6'):
                    ui.icon('lan', size='md', color='#6366f1')
                    ui.label('Connection').style('font-size: 1.5rem; font-weight: 600; color: var(--text-color);')
                
                with ui.column().classes('w-full gap-5'):
                    is_local = ui.switch('Install Locally?', value=True).props('color="primary"')
                    
                    with ui.row().classes('w-full gap-4').bind_visibility_from(is_local, 'value', backward=lambda v: not v):
                        host_input = ui.input('Host').props('outlined rounded color="primary"').classes('flex-grow').style('transition: all 0.3s ease;')
                        username_input = ui.input('Username').props('outlined rounded color="primary"').classes('flex-grow')
                        ssh_port_input = ui.input('SSH Port', value='22').props('outlined rounded color="primary"').classes('w-24')

                    with ui.column().classes('w-full gap-3').bind_visibility_from(is_local, 'value', backward=lambda v: not v):
                        ui.label('SSH Authentication').style('font-weight: 500; color: var(--text-muted); font-size: 0.9rem;')
                        key_path_input = ui.input('Private Key Path', value='~/.ssh/volttron_installer').props('outlined rounded color="primary"').classes('w-full')
                        ui.label('Remote deployments use SSH keys only. Create a key on this installer host and add its public key to the remote user.').style('font-size: 0.8rem; color: var(--text-muted);')
                        with ui.expansion('How to create an SSH key', icon='key').classes('w-full').props('header-class="text-muted"'):
                            with ui.column().classes('w-full gap-2 p-4').style('background: var(--code-bg); border: 1px solid var(--code-border); border-radius: 6px;'):
                                ui.label('Run these commands on the machine running this installer:').style('color: var(--text-color); font-size: 0.85rem;')
                                ui.code(
                                    'ssh-keygen -t ed25519 -f ~/.ssh/volttron_installer -C volttron-installer\n'
                                    'ssh-copy-id -i ~/.ssh/volttron_installer.pub USER@REMOTE_HOST\n'
                                    'ssh -i ~/.ssh/volttron_installer USER@REMOTE_HOST',
                                    language='bash',
                                ).classes('w-full').style('background: var(--code-bg); color: var(--text-color); border: 1px solid var(--code-border);')
                                ui.label('After the test SSH command works, use ~/.ssh/volttron_installer as the private key path above.').style('color: var(--text-muted); font-size: 0.8rem;')
                    
                    with ui.expansion('Advanced Settings', icon='settings').classes('w-full').props('header-class="text-muted"'):
                         with ui.column().classes('w-full gap-4 p-4'):
                            with ui.row().classes('w-full gap-4'):
                                ui.input('HTTP Proxy').props('outlined dense color="primary"').classes('flex-grow')
                                ui.input('HTTPS Proxy').props('outlined dense color="primary"').classes('flex-grow')
                            with ui.row().classes('w-full gap-4'):
                                volttron_home_input = ui.input('VOLTTRON Home', value=f'~/.{default_name}').props('outlined dense color="primary"').classes('flex-grow')
                                venv_input = ui.input('VOLTTRON venv', value=f'~/.{default_name}.venv').props('outlined dense color="primary"').classes('flex-grow')
                            ui.input('Custom Python Path').props('outlined dense color="primary"').classes('w-full')
                            ignore_host_keys_checkbox = ui.checkbox('Ignore Host Keys (StrictHostKeyChecking=no)').props('color="primary"')
 
            # Instance Configuration Section
            with ui.card().classes('w-full').style('background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--card-border); border-radius: 16px; padding: 2rem; box-shadow: var(--card-shadow); transition: transform 0.3s ease, border-color 0.3s ease;').on('mouseenter', lambda e: e.sender.style('border-color: rgba(168, 85, 247, 0.5);')).on('mouseleave', lambda e: e.sender.style('border-color: rgba(255, 255, 255, 0.1);')):
                with ui.row().classes('items-center gap-3 mb-6'):
                    ui.icon('tune', size='md', color='#a855f7')
                    ui.label('Instance Configuration').style('font-size: 1.5rem; font-weight: 600; color: var(--text-color);')
                
                with ui.column().classes('w-full gap-6'):
                    def update_paths(e):
                        volttron_home_input.value = f'~/.{e.value}'
                        venv_input.value = f'~/.{e.value}.venv'
                        
                    instance_name_input = ui.input('Instance Name', value=default_name, on_change=update_paths).props('outlined rounded color="primary"').classes('w-full')
                    
                    with ui.column().classes('w-full gap-2'):
                        ui.label('VOLTTRON Type').style('font-weight: 500; color: var(--text-muted); font-size: 0.9rem;')
                        type_toggle = ui.toggle(['Modular', 'Monolithic'], value='Modular').props('color="primary" rounded spread').classes('w-full')
                        ui.label('Modular: Agents are pip packages (recommended). Monolithic: Bundled all-in-one.').style('font-size: 0.8rem; color: var(--text-muted);')
                    
                    with ui.column().classes('w-full gap-2'):
                        ui.label('Package Source').style('font-weight: 500; color: var(--text-muted); font-size: 0.9rem;')
                        package_source = ui.toggle(['Automatic', 'Manual'], value='Automatic').props('color="primary" rounded spread').classes('w-full')
                        
                        with ui.column().classes('w-full gap-4 p-4 border border-gray-700 rounded-lg bg-[var(--sub-bg)] mt-2').bind_visibility_from(package_source, 'value', backward=lambda v: v == 'Manual'):
                            ui.label('Manual Package Overrides').style('font-weight: 600; color: var(--text-color); font-size: 0.9rem;')
                            core_pkg_input = ui.input('Core Package', placeholder='eclipse-volttron/volttron-core@main').props('outlined dense color="primary"').classes('w-full')
                            auth_pkg_input = ui.input('Auth Package', placeholder='eclipse-volttron/volttron-lib-auth@main').props('outlined dense color="primary"').classes('w-full')
                            zmq_pkg_input = ui.input('ZMQ Package', placeholder='eclipse-volttron/volttron-lib-zmq@main').props('outlined dense color="primary"').classes('w-full')
                            tree_pkg_input = ui.input('Tree Package', placeholder='eclipse-volttron/volttron-lib-tree@main').props('outlined dense color="primary"').classes('w-full')
                            web_pkg_input = ui.input('Web Package', placeholder='eclipse-volttron/volttron-lib-web@main').props('outlined dense color="primary"').classes('w-full')
                    
                    vip_input = ui.input('VIP Address').props('outlined rounded color="primary"').classes('w-full')
                    
                    with ui.row().classes('w-full justify-between items-center bg-[var(--sub-bg)] p-4 rounded-xl border border-gray-800'):
                        with ui.column().classes('gap-1'):
                            ui.label('Web Interface').style('font-weight: 600; color: var(--text-color);')
                            ui.label('Browser-based platform management and monitoring').style('font-size: 0.8rem; color: var(--text-muted);')
                        web_interface_toggle = ui.switch(value=True).props('color="primary"')
                        
                    with ui.row().classes('w-full justify-between items-center bg-[var(--sub-bg)] p-4 rounded-xl border border-gray-800'):
                        with ui.column().classes('gap-1'):
                            ui.label('Federation').style('font-weight: 600; color: var(--text-color);')
                            ui.label('Connect this platform to a multi-platform VOLTTRON federation').style('font-size: 0.8rem; color: var(--text-muted);')
                        ui.switch(value=False).props('color="primary"')
 
            # Pre-Deployment Agents Section
            with ui.card().classes('w-full').style('background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--card-border); border-radius: 16px; padding: 2rem; box-shadow: var(--card-shadow); transition: transform 0.3s ease, border-color 0.3s ease;').on('mouseenter', lambda e: e.sender.style('border-color: rgba(236, 72, 153, 0.5);')).on('mouseleave', lambda e: e.sender.style('border-color: rgba(255, 255, 255, 0.1);')):
                with ui.row().classes('items-center gap-3 mb-2'):
                    ui.icon('smart_toy', size='md', color='#ec4899')
                    ui.label('Pre-Deployment Agents').style('font-size: 1.5rem; font-weight: 600; color: var(--text-color);')
                ui.label('Select agents to install during deployment.').style('color: var(--text-muted); margin-bottom: 1.5rem;')
                
                with ui.row().classes('w-full gap-8'):
                    with ui.column().classes('flex-1 gap-3'):
                        ui.label('Available').style('font-weight: 600; color: var(--text-color); border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; width: 100%;')
                        for agent in ['ListenerAgent', 'VCPLogger', 'PlatformAgent']:
                            with ui.row().classes('w-full justify-between items-center bg-[var(--sub-bg)] p-3 rounded-lg border border-gray-800'):
                                ui.label(agent).style('color: var(--text-color);')
                                ui.button(icon='add').props('flat round dense color="primary"')
                                
                    ui.separator().props('vertical')
                    
                    with ui.column().classes('flex-1 gap-3'):
                        ui.label('Selected').style('font-weight: 600; color: var(--text-color); border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; width: 100%;')
                        with ui.row().classes('w-full justify-center p-6 border border-dashed border-gray-700 rounded-lg'):
                            ui.label('No agents selected').style('color: var(--text-muted); font-style: italic;')
 
            # Action Buttons
            with ui.row().classes('w-full justify-end gap-4 mt-4'):
                cancel_btn = ui.button('Cancel', on_click=lambda: ui.navigate.to('/')).props('outline rounded size="lg"').style('padding: 10px 30px; font-weight: bold; transition: all 0.2s ease;')
                binding.bind_from(cancel_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                cancel_btn.on('mouseenter', lambda e: e.sender.style('background: var(--card-border);')).on('mouseleave', lambda e: e.sender.style('background: transparent;'))
                
                ui.button('Save & Deploy', on_click=perform_install).props('color="positive" rounded size="lg"').style('padding: 10px 30px; font-weight: bold; background: linear-gradient(90deg, #10b981, #059669); color: white; transition: transform 0.2s ease, box-shadow 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: scale(1.05); box-shadow: 0 0 15px rgba(16, 185, 129, 0.5);')).on('mouseleave', lambda e: e.sender.style('transform: scale(1); box-shadow: none;'))
