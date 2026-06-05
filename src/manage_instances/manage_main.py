from nicegui import ui, binding
import json
from urllib.parse import quote

import src.db as db
from src import ssh_remote
from src import theme
from src.manage_instances import agent_management
from src.manage_instances.log_parser import push_logs_to_ui

DEFAULT_LIBRARY_NAMES = {
    'volttron-lib-auth',
    'volttron-lib-base-driver',
    'volttron-lib-tree',
    'volttron-lib-web',
    'volttron-lib-zmq',
}

def render(instance_name: str):
    dark_mode = theme.dark_mode()
    instances = db.get_instances()
    instance = next((i for i in instances if i.get('name') == instance_name), None)
    
    if not instance:
        with ui.column().classes('w-full items-center py-20'):
            ui.label(f'Instance "{instance_name}" not found').classes('text-red-500 text-2xl font-bold mb-4')
            back_btn = ui.button('Back to Instances', on_click=lambda: ui.navigate.to('/instances')).props('outline')
            binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
        return

    agents_container = None
    libraries_container = None
    log_container = None
    install_dialog = None
    install_library_dialog = None
    agent_source_input = None
    agent_identity_input = None
    agent_config_input = None
    agent_start_switch = None
    library_source_input = None
    library_force_switch = None
    library_prerelease_switch = None
    log_view = None
    log_follow_switch = None
    start_button = None
    shutdown_button = None
    install_agent_button = None
    install_library_button = None
    current_platform_state = 'unknown'
    active_log_name = 'volttron.log'
    last_log_content = None
    last_agents_signature = None
    last_libraries_signature = None
    agent_refresh_in_progress = False
    library_refresh_in_progress = False
    ssh_refresh_in_progress = False

    def remote_password_needed() -> bool:
        return ssh_remote.needs_key(instance)

    def render_log_entries(content: str) -> None:
        if log_view is not None:
            push_logs_to_ui(content, log_view)

    def render_ssh_needed(container, message: str):
        container.clear()
        with container:
            with ui.column().classes('w-full min-h-24 items-center justify-center gap-2 border border-dashed rounded-md'):
                ui.icon('key', size='sm', color='gray')
                ui.label(message).classes(theme.muted())

    def set_platform_status(text: str, color: str, state: str = 'unknown'):
        nonlocal current_platform_state
        previous_state = current_platform_state
        current_platform_state = state
        status_badge.set_text(text)
        status_badge.props(f'color="{color}"')
        if start_button is not None:
            start_button.set_enabled(state in {'stopped', 'unknown'})
        if shutdown_button is not None:
            shutdown_button.set_enabled(state == 'running')
        if install_agent_button is not None:
            install_agent_button.set_enabled(state == 'running')
        if install_library_button is not None:
            install_library_button.set_enabled(state == 'running')
        if previous_state != state and agents_container is not None:
            ui.timer(0.1, refresh_agents, once=True)
        if previous_state != state and libraries_container is not None:
            ui.timer(0.1, refresh_libraries, once=True)

    def show_command_error(title: str, error: Exception):
        error_log_container.clear()
        error_log_container.visible = True
        stdout = getattr(error, 'stdout', '')
        stderr = getattr(error, 'stderr', '')
        details = f"{error}\n\n"
        if stderr:
            details += f"stderr:\n{stderr}\n"
        if stdout:
            details += f"stdout:\n{stdout}\n"
        with error_log_container:
            ui.label(title).classes('text-red-500 font-bold text-lg mb-2')
            ui.code(details).classes('w-full text-negative border border-negative whitespace-pre-wrap')

    async def refresh_agents():
        nonlocal agent_refresh_in_progress, last_agents_signature
        if agents_container is None:
            return
        if agent_refresh_in_progress:
            return
        if remote_password_needed():
            signature = ('ssh-password-needed',)
            if signature == last_agents_signature:
                return
            last_agents_signature = signature
            render_ssh_needed(agents_container, 'Configure an SSH key path to view agents.')
            return
        if current_platform_state != 'running':
            signature = ('platform-not-running', current_platform_state)
            if signature == last_agents_signature:
                return
            last_agents_signature = signature
            agents_container.clear()
            with agents_container:
                with ui.column().classes('w-full items-center justify-center gap-2 py-8 text-grey-6'):
                    ui.icon('power_settings_new', size='sm', color='gray')
                    ui.label('Start VOLTTRON to view installed agents.')
            return
        try:
            agent_refresh_in_progress = True
            agents = await agent_management.list_agents(instance)
        except Exception as e:
            signature = ('error', str(e))
            if signature == last_agents_signature:
                return
            last_agents_signature = signature
            agents_container.clear()
            with agents_container:
                with ui.column().classes('w-full items-center justify-center gap-2 py-8 text-negative'):
                    ui.icon('error_outline', size='md', color='red')
                    ui.label(f'Could not load agents: {e}')
            return
        finally:
            agent_refresh_in_progress = False

        signature = tuple(
            (agent.get('identity'), agent.get('uuid'), agent.get('state'), agent.get('status'), agent.get('health'))
            for agent in agents
        )
        if signature == last_agents_signature:
            return
        last_agents_signature = signature
        agents_container.clear()

        with agents_container:
            if not agents:
                with ui.column().classes('w-full items-center justify-center gap-2 py-8 text-grey-6'):
                    ui.icon('extension_off', size='sm', color='gray')
                    ui.label('No agents installed')
                return

            with ui.list().classes('w-full').props('separator'):
                for agent in agents:
                    agent_id = agent.get('uuid') or agent.get('identity')
                    agent_identity = agent.get('identity', 'unknown')
                    is_running = agent.get('state') == 'running'
                    detail = agent.get('status') or agent.get('uuid') or 'No status detail'

                    async def do_start(agent_ref=agent_id):
                        try:
                            await agent_management.start_agent(instance, agent_ref)
                            ui.notify('Agent start command sent', type='positive')
                            await refresh_agents()
                        except Exception as e:
                            ui.notify(f'Failed to start agent: {e}', type='negative')
                            show_command_error('Agent Start Error', e)

                    async def do_stop(agent_ref=agent_id):
                        try:
                            await agent_management.stop_agent(instance, agent_ref)
                            ui.notify('Agent stop command sent', type='positive')
                            await refresh_agents()
                        except Exception as e:
                            ui.notify(f'Failed to stop agent: {e}', type='negative')
                            show_command_error('Agent Stop Error', e)

                    async def do_remove(agent_ref=agent_id, label=agent_identity):
                        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4 min-w-96'):
                            ui.label(f'Remove {label}?').classes('text-lg font-bold')
                            ui.label('This uninstalls the agent from the running platform.').classes('text-grey-6')
                            with ui.row().classes('justify-end w-full gap-2'):
                                ui.button('Cancel', on_click=confirm_dialog.close).props('flat')

                                async def confirm_remove():
                                    confirm_dialog.close()
                                    try:
                                        await agent_management.remove_agent(instance, agent_ref)
                                        ui.notify('Agent removed', type='positive')
                                        await refresh_agents()
                                    except Exception as e:
                                        ui.notify(f'Failed to remove agent: {e}', type='negative')
                                        show_command_error('Agent Remove Error', e)

                                ui.button('Remove', icon='delete', on_click=confirm_remove).props('color="negative"')
                        confirm_dialog.open()

                    with ui.item().classes('px-0 py-3'):
                        with ui.item_section():
                            with ui.row().classes('items-center gap-2'):
                                ui.item_label(agent_identity).classes('font-bold')
                                ui.badge('running' if is_running else 'stopped', color='positive' if is_running else 'grey')
                            ui.item_label(detail).props('caption')
                            if agent.get('health'):
                                ui.item_label(agent.get('health')).props('caption').classes('text-positive')

                        with ui.item_section().props('side'):
                            with ui.row().classes('items-center gap-1'):
                                ui.button(
                                    icon='settings',
                                    on_click=lambda agent_ref=agent_identity: ui.navigate.to(
                                        f'/manage/{quote(instance_name, safe="")}/config-store/{quote(agent_ref, safe="")}'
                                    ),
                                ).props('flat round color="primary"').tooltip('Config store')
                                if is_running:
                                    ui.button(icon='stop', on_click=do_stop).props('flat round color="warning"').tooltip('Stop agent')
                                else:
                                    ui.button(icon='play_arrow', on_click=do_start).props('flat round color="positive"').tooltip('Start agent')
                                ui.button(icon='delete', on_click=do_remove).props('flat round color="negative"').tooltip('Remove agent')

    async def refresh_libraries():
        nonlocal library_refresh_in_progress, last_libraries_signature
        if libraries_container is None:
            return
        if library_refresh_in_progress:
            return
        if remote_password_needed():
            signature = ('ssh-password-needed',)
            if signature == last_libraries_signature:
                return
            last_libraries_signature = signature
            render_ssh_needed(libraries_container, 'Configure an SSH key path to view libraries.')
            return

        try:
            library_refresh_in_progress = True
            libraries = await agent_management.list_libraries(instance)
        except Exception as e:
            signature = ('error', str(e))
            if signature == last_libraries_signature:
                return
            last_libraries_signature = signature
            libraries_container.clear()
            with libraries_container:
                with ui.column().classes('w-full items-center justify-center gap-2 py-8 text-negative'):
                    ui.icon('error_outline', size='md', color='red')
                    ui.label(f'Could not load libraries: {e}')
            return
        finally:
            library_refresh_in_progress = False

        signature = (
            current_platform_state,
            tuple((library.get('name'), library.get('version')) for library in libraries),
        )
        if signature == last_libraries_signature:
            return
        last_libraries_signature = signature
        libraries_container.clear()

        with libraries_container:
            default_libraries = []
            additional_libraries = []
            for library in libraries:
                normalized_name = (library.get('name') or '').lower().replace('_', '-')
                if normalized_name in DEFAULT_LIBRARY_NAMES:
                    default_libraries.append(library)
                else:
                    additional_libraries.append(library)

            if not libraries:
                with ui.column().classes('w-full items-center justify-center gap-2 py-8 text-grey-6'):
                    ui.icon('inventory_2', size='sm', color='gray')
                    ui.label('No VOLTTRON libraries installed')
                return

            def render_library_row(library: dict, removable: bool = True):
                library_name = library.get('name', 'unknown')
                library_version = library.get('version') or 'unknown version'

                async def do_remove_library(lib_name=library_name):
                    with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4 min-w-96'):
                        ui.label(f'Remove {lib_name}?').classes('text-lg font-bold')
                        ui.label('This removes the library package from the selected platform environment. Agents that depend on it may stop working.').classes('text-grey-6')
                        with ui.row().classes('justify-end w-full gap-2'):
                            ui.button('Cancel', on_click=confirm_dialog.close).props('flat')
                            async def confirm_remove_library():
                                confirm_dialog.close()
                                try:
                                    await agent_management.remove_library(instance, lib_name)
                                    ui.notify('Library removed', type='positive')
                                    await refresh_libraries()
                                    await refresh_agents()
                                except Exception as e:
                                    ui.notify(f'Failed to remove library: {e}', type='negative')
                                    show_command_error('Library Remove Error', e)
                            ui.button('Remove', icon='delete', on_click=confirm_remove_library).props('color="negative"')
                    confirm_dialog.open()

                with ui.item().classes('px-0 py-3'):
                    with ui.item_section():
                        ui.item_label(library_name).classes('font-bold')
                        ui.item_label(library_version).props('caption')
                    if removable:
                        with ui.item_section().props('side'):
                            ui.button(icon='delete', on_click=do_remove_library).props('flat round color="negative"').tooltip('Remove library').set_enabled(current_platform_state == 'running')

            if additional_libraries:
                with ui.list().classes('w-full').props('separator'):
                    for library in additional_libraries:
                        render_library_row(library)
            else:
                with ui.column().classes('w-full items-center justify-center gap-2 py-8 text-grey-6'):
                    ui.icon('extension_off', size='sm', color='gray')
                    ui.label('No additional VOLTTRON libraries installed')

            if default_libraries:
                with ui.expansion(f'Default Libraries ({len(default_libraries)})', icon='inventory_2').classes('w-full mt-3'):
                    with ui.list().classes('w-full').props('separator'):
                        for library in default_libraries:
                            render_library_row(library, removable=False)

    async def refresh_log():
        nonlocal last_log_content, ssh_refresh_in_progress
        if log_view is None:
            return
        if ssh_refresh_in_progress:
            return
        if remote_password_needed():
            content = 'Configure an SSH key path to view the remote log.'
        else:
            try:
                ssh_refresh_in_progress = True
                content = await agent_management.read_log_tail(instance, 300, active_log_name)
            except ssh_remote.SSHCommandError as exc:
                content = f"SSH unavailable: {exc}"
            except Exception as exc:
                content = f"Could not read log: {exc}"
            finally:
                ssh_refresh_in_progress = False
        if content == last_log_content:
            return
        last_log_content = content
        render_log_entries(content)

    async def handle_log_selection(event):
        nonlocal active_log_name, last_log_content
        active_log_name = event.value or 'volttron.log'
        last_log_content = None
        await refresh_log()

    async def handle_clear_log():
        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4'):
            ui.label(f'Clear {active_log_name}?').classes('text-lg font-bold')
            ui.label('This truncates the current log file for this instance. New log entries will still appear here.').classes(theme.muted())
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=confirm_dialog.close).props('flat color="gray"')

                async def confirm_clear():
                    nonlocal last_log_content
                    confirm_dialog.close()
                    try:
                        await agent_management.clear_log(instance, active_log_name)
                        last_log_content = None
                        await refresh_log()
                        ui.notify(f'{active_log_name} cleared', type='positive')
                    except Exception as e:
                        ui.notify(f'Failed to clear log: {e}', type='negative')
                        show_command_error('Clear Log Error', e)

                ui.button('Clear Log', icon='delete_sweep', on_click=confirm_clear).props('color="negative"')
        confirm_dialog.open()

    async def handle_install_agent():
        source = (agent_source_input.value or '').strip()
        identity = (agent_identity_input.value or '').strip()
        config = (agent_config_input.value or '').strip()
        start = bool(agent_start_switch.value)

        if not source:
            ui.notify('Agent source is required', type='warning')
            return

        install_dialog.close()
        with ui.dialog() as progress_dialog, ui.card().classes('p-8 items-center gap-4'):
            ui.label('Installing Agent').classes('text-xl font-bold')
            ui.spinner(size='lg')
            ui.label(source).classes(theme.muted())
        progress_dialog.open()
        try:
            await agent_management.install_agent(instance, source, identity, start, config)
            progress_dialog.close()
            ui.notify('Agent installed successfully', type='positive')
            error_log_container.visible = False
            await refresh_agents()
        except Exception as e:
            progress_dialog.close()
            ui.notify(f'Failed to install agent: {e}', type='negative')
            show_command_error('Agent Install Error', e)

    async def handle_install_library():
        source = (library_source_input.value or '').strip()
        force = bool(library_force_switch.value)
        allow_prerelease = bool(library_prerelease_switch.value)

        if not source:
            ui.notify('Library source is required', type='warning')
            return

        install_library_dialog.close()
        with ui.dialog() as progress_dialog, ui.card().classes('p-8 items-center gap-4'):
            ui.label('Installing Library').classes('text-xl font-bold')
            ui.spinner(size='lg')
            ui.label(source).classes(theme.muted())
        progress_dialog.open()
        try:
            await agent_management.install_library(instance, source, force, allow_prerelease)
            progress_dialog.close()
            ui.notify('Library installed successfully', type='positive')
            error_log_container.visible = False
            await refresh_libraries()
        except Exception as e:
            progress_dialog.close()
            ui.notify(f'Failed to install library: {e}', type='negative')
            show_command_error('Library Install Error', e)

    async def handle_shutdown():
        async def run_shutdown(sudo_password: str = ''):
            try:
                shutdown_message = await agent_management.shutdown_platform(instance, sudo_password=sudo_password)
                ui.notify(f'{instance_name} shut down', type='positive')
                if shutdown_message:
                    ui.notify(shutdown_message, type='info')
                error_log_container.clear()
                error_log_container.visible = False
                await check_status()
                await refresh_agents()
                await refresh_log()
            except Exception as e:
                if (
                    not sudo_password
                    and instance.get('deployment_method') == 'ansible'
                    and instance.get('is_local', True)
                    and 'interactive authentication is required' in str(e)
                ):
                    with ui.dialog() as sudo_dialog, ui.card().classes('p-6 gap-4 w-full max-w-lg'):
                        ui.label('Sudo Password Required').classes('text-lg font-bold')
                        ui.label(f'Stopping {instance_name} uses systemd and needs sudo on this machine. The password is used once and is not saved.').classes(theme.muted())
                        sudo_password_input = ui.input('Local sudo password', password=True, password_toggle_button=True).props('outlined autocomplete="current-password"').classes('w-full')
                        with ui.row().classes('justify-end w-full gap-2'):
                            ui.button('Cancel', on_click=sudo_dialog.close).props('flat color="gray"')

                            async def retry_shutdown():
                                password = sudo_password_input.value or ''
                                if not password:
                                    ui.notify('Enter your sudo password to stop the service.', type='warning')
                                    return
                                sudo_dialog.close()
                                await run_shutdown(password)

                            ui.button('Stop Service', icon='power_settings_new', on_click=retry_shutdown).props('color="negative"')
                    sudo_dialog.open()
                    return

                ui.notify(f'Failed to shut down: {e}', type='negative')
                show_command_error('Shutdown Error', e)
                await check_status()

        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4'):
            ui.label(f'Shut down {instance_name}?').classes('text-lg font-bold')
            ui.label('This stops the selected platform. Ansible deployments use the systemd service.').classes(theme.muted())
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=confirm_dialog.close).props('flat color="gray"')
                async def confirm_shutdown():
                    confirm_dialog.close()
                    await run_shutdown()
                ui.button('Shut Down', icon='power_settings_new', on_click=confirm_shutdown).props('color="negative"')
        confirm_dialog.open()

    async def handle_delete_platform():
        venv_path = instance.get('venv') or 'N/A'
        volttron_home = instance.get('volttron_home') or 'N/A'
        service_name = f"volttron-{instance_name}.service"
        needs_local_sudo = instance.get('deployment_method') == 'ansible' and instance.get('is_local', True)
        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4 w-full max-w-xl'):
            ui.label(f'Delete {instance_name}?').classes('text-lg font-bold text-red-400')
            ui.label('This will stop and remove its systemd service, delete its virtual environment, delete VOLTTRON_HOME, and remove it from this installer.').classes(theme.muted())
            with ui.column().classes('w-full gap-1 p-3 border rounded-md'):
                if instance.get('deployment_method') == 'ansible':
                    ui.label(f'Systemd Service: {service_name}').classes(theme.small_muted())
                ui.label(f'Virtual Env: {venv_path}').classes(theme.small_muted())
                ui.label(f'VOLTTRON Home: {volttron_home}').classes(theme.small_muted())
                ui.label(f'Instance Record: instances_data/{instance_name}.json').classes(theme.small_muted())
            sudo_password_input = None
            if needs_local_sudo:
                ui.label('Local sudo is required to remove the systemd service. The password is used once and is not saved.').classes(theme.small_muted())
                sudo_password_input = ui.input('Local sudo password', password=True, password_toggle_button=True).props('outlined autocomplete="current-password"').classes('w-full')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=confirm_dialog.close).props('flat color="gray"')

                async def confirm_delete():
                    sudo_password = sudo_password_input.value or '' if sudo_password_input is not None else ''
                    if needs_local_sudo and not sudo_password:
                        ui.notify('Enter your sudo password to remove the service.', type='warning')
                        return
                    confirm_dialog.close()
                    with ui.dialog() as progress_dialog, ui.card().classes('p-8 items-center gap-4'):
                        ui.label('Deleting Platform').classes('text-xl font-bold')
                        ui.spinner(size='lg')
                        ui.label(instance_name).classes(theme.muted())
                    progress_dialog.open()
                    try:
                        messages = await agent_management.delete_platform_files(instance, sudo_password=sudo_password)
                        db.delete_instance(instance_name)
                        progress_dialog.close()
                        ui.notify(f'{instance_name} deleted', type='positive')
                        for message in messages:
                            ui.notify(message, type='info')
                        ui.navigate.to('/instances')
                    except Exception as e:
                        progress_dialog.close()
                        ui.notify(f'Failed to delete platform: {e}', type='negative')
                        show_command_error('Delete Platform Error', e)

                ui.button('Delete Platform', icon='delete_forever', on_click=confirm_delete).props('color="negative"')
        confirm_dialog.open()

    with ui.column().classes(theme.page_container('py-8 px-4')):
        # Header
        with ui.column().classes('w-full max-w-6xl gap-4 mb-8'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-3'):
                    back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/instances')).props('flat round')
                    binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    ui.label(instance_name).classes('text-3xl font-bold')
                
                with ui.row().classes('items-center gap-3'):
                    status_badge = ui.badge('Checking Status...', color='gray').classes('text-sm px-3 py-2')
                    theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
                    theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
                    binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')
                
            async def check_status():
                from src.manage_instances.status_check import check_volttron_rest_status, is_port_bound
                import re
                
                rest_result = await check_volttron_rest_status(instance)
                if rest_result['status'] == 'running':
                    set_platform_status('VOLTTRON Running', 'positive', 'running')
                    return
                if rest_result['status'] == 'stopped':
                    set_platform_status('VOLTTRON Stopped', 'red', 'stopped')
                    return
                if rest_result['status'] == 'degraded':
                    set_platform_status('VOLTTRON Web Offline', 'warning', 'unknown')
                    return

                # Fallback for instances that do not have the web API configured yet.
                vip_address = instance.get('vip', '')
                is_running = False
                
                if vip_address:
                    match = re.match(r"^tcp://([^:]+):(\d+)$", vip_address)
                    if match:
                        host = match.group(1)
                        if host in ['*', '0.0.0.0']: host = '127.0.0.1'
                        port = int(match.group(2))
                        is_running = is_port_bound(host, port)

                if is_running:
                    set_platform_status('VOLTTRON Running (VIP Only)', 'warning', 'running')
                else:
                    set_platform_status('VOLTTRON Status Unknown', 'gray', 'unknown')
                    
            # Check immediately and then every 5 seconds
            ui.timer(0.1, check_status, once=True)
            if instance.get('is_local', True):
                ui.timer(5.0, check_status)
            
            async def handle_start():
                from src.manage_instances.start_platform import start_platform_command
                ui.notify(f'Starting {instance_name}...', type='info')

                async def run_start(sudo_password: str = ''):
                    with ui.dialog() as dialog, ui.card().classes('p-8 items-center gap-4'):
                        ui.label('Starting Platform').classes('text-xl font-bold')
                        ui.spinner(size='lg')
                        ui.label('Waiting for initialization...')
                    dialog.open()

                    try:
                        await start_platform_command(instance.get('venv'), instance.get('volttron_home'), instance, sudo_password=sudo_password)
                        dialog.close()
                        ui.notify(f'{instance_name} started successfully!', type='positive')
                        error_log_container.clear()
                        error_log_container.visible = False
                        set_platform_status('VOLTTRON Running', 'positive', 'running')
                        await check_status()
                        await refresh_agents()
                        await refresh_log()
                    except Exception as e:
                        dialog.close()
                        if (
                            not sudo_password
                            and instance.get('deployment_method') == 'ansible'
                            and instance.get('is_local', True)
                            and 'interactive authentication is required' in str(e)
                        ):
                            with ui.dialog() as sudo_dialog, ui.card().classes('p-6 gap-4 w-full max-w-lg'):
                                ui.label('Sudo Password Required').classes('text-lg font-bold')
                                ui.label(f'Starting {instance_name} uses systemd and needs sudo on this machine. The password is used once and is not saved.').classes(theme.muted())
                                sudo_password_input = ui.input('Local sudo password', password=True, password_toggle_button=True).props('outlined autocomplete="current-password"').classes('w-full')
                                with ui.row().classes('justify-end w-full gap-2'):
                                    ui.button('Cancel', on_click=sudo_dialog.close).props('flat color="gray"')

                                    async def retry_start():
                                        password = sudo_password_input.value or ''
                                        if not password:
                                            ui.notify('Enter your sudo password to start the service.', type='warning')
                                            return
                                        sudo_dialog.close()
                                        await run_start(password)

                                    ui.button('Start Service', icon='play_arrow', on_click=retry_start).props('color="positive"')
                            sudo_dialog.open()
                            return

                        ui.notify(f'Failed to start: {str(e)}', type='negative')
                        await check_status()

                        log_content = f"Error: {str(e)}\n\n"
                        try:
                            log_content += await agent_management.read_log_tail(instance, 20)
                        except Exception as log_err:
                            log_content += f"Could not read log file: {log_err}"

                        error_log_container.clear()
                        error_log_container.visible = True
                        with error_log_container:
                            ui.label('Startup Error (Last 20 lines of volttron.log)').classes('text-red-500 font-bold text-lg mb-2')
                            ui.code(log_content).classes('w-full text-negative border border-negative')

                await run_start()

            with ui.row().classes('gap-2 items-center'):
                start_button = ui.button('Start', icon='play_arrow', on_click=handle_start).props('color="positive" unelevated').classes('font-semibold min-w-28')
                shutdown_button = ui.button('Shut Down', icon='power_settings_new', on_click=handle_shutdown).props('outline color="negative"').classes('font-semibold min-w-32')
                ui.button('Delete', icon='delete_forever', on_click=handle_delete_platform).props('flat color="negative"').classes('font-semibold min-w-24')
                start_button.disable()
                shutdown_button.disable()

        with ui.column().classes('w-full max-w-6xl gap-5'):
            def copy_button(command: str, label: str):
                button = ui.button(icon='content_copy').props('flat round dense color="primary"')
                button.on('click', js_handler=f'''
                    async () => {{
                        const text = {json.dumps(command)};
                        try {{
                            if (navigator.clipboard && window.isSecureContext) {{
                                await navigator.clipboard.writeText(text);
                            }} else {{
                                const textarea = document.createElement('textarea');
                                textarea.value = text;
                                textarea.setAttribute('hidden', '');
                                document.body.appendChild(textarea);
                                textarea.focus();
                                textarea.select();
                                document.execCommand('copy');
                                document.body.removeChild(textarea);
                            }}
                        }} catch (error) {{
                            const textarea = document.createElement('textarea');
                            textarea.value = text;
                            textarea.setAttribute('hidden', '');
                            document.body.appendChild(textarea);
                            textarea.focus();
                            textarea.select();
                            document.execCommand('copy');
                            document.body.removeChild(textarea);
                        }}
                    }}
                ''')
                ui.tooltip(f'Copy {label} command')
                return button

            def row_label(key, value, copy_command: str | None = None, copy_label: str = ''):
                with ui.item().classes('px-0'):
                    with ui.item_section():
                        ui.item_label(key).props('caption')
                    with ui.item_section().props('side'):
                        with ui.row().classes('items-center gap-1 no-wrap'):
                            ui.item_label(value).classes('font-medium')
                            if copy_command:
                                copy_button(copy_command, copy_label or key)

            with ui.expansion('Platform Information', icon='info').classes('w-full'):
                with ui.list().classes('w-full').props('separator'):
                    row_label('Type', instance.get('type', 'Modular'))
                    row_label('Host', instance.get('host', 'localhost'))
                    row_label('Local Install', 'Yes' if instance.get('is_local') else 'No')
                    row_label('VIP Address', instance.get('vip') or 'N/A')
                    volttron_home = instance.get('volttron_home', 'N/A')
                    venv_path = instance.get('venv', 'N/A')
                    row_label(
                        'VOLTTRON Home',
                        volttron_home,
                        None if volttron_home == 'N/A' else f'export VOLTTRON_HOME={volttron_home}',
                        'VOLTTRON_HOME',
                    )
                    row_label(
                        'Virtual Env',
                        venv_path,
                        None if venv_path == 'N/A' else f'source {venv_path.rstrip("/")}/bin/activate',
                        'venv activation',
                    )
                    if not instance.get('is_local', True):
                        row_label('SSH User', instance.get('ssh_username', 'N/A'))
                        row_label('SSH Port', str(instance.get('ssh_port', '22')))
                        row_label('SSH Key', instance.get('ssh_key_path') or 'Agent/default keys')
                        ui.item_label('Remote management uses SSH keys only.').props('caption').classes('px-0 py-2')

            # Agents
            with ui.column().classes('w-full gap-4'):
                with ui.row().classes('items-center gap-2 mb-4 justify-between w-full'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('smart_toy', size='sm', color='accent')
                        ui.label('Installed Agents').classes('text-xl font-bold')
                    
                    install_agent_button = ui.button('Install Agent', icon='add', on_click=lambda: install_dialog.open()).props('outline color="primary"')
                    install_agent_button.disable()
                
                ui.separator()
                
                agents_container = ui.column().classes('w-full gap-0')
                ui.timer(0.2, refresh_agents, once=True)
                if instance.get('is_local', True):
                    ui.timer(8.0, refresh_agents)

        with ui.column().classes('w-full max-w-6xl gap-4 mt-5'):
            with ui.row().classes('items-center gap-2 mb-4 justify-between w-full'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('extension', size='sm', color='warning')
                    ui.label('Installed Libraries').classes('text-xl font-bold')

                with ui.row().classes('items-center gap-2'):
                    refresh_lib_btn = ui.button(icon='refresh', on_click=refresh_libraries).props('flat round').tooltip('Refresh libraries')
                    binding.bind_from(refresh_lib_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    install_library_button = ui.button('Install Library', icon='add', on_click=lambda: install_library_dialog.open()).props('outline color="primary"')
                    install_library_button.disable()

            ui.separator()

            libraries_container = ui.column().classes('w-full gap-0')
            ui.timer(0.4, refresh_libraries, once=True)
            if instance.get('is_local', True):
                ui.timer(20.0, refresh_libraries)

        with ui.card().classes(theme.card('max-w-6xl mt-5')):
            with ui.row().classes('items-center justify-between w-full mb-4'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('article', size='sm', color='positive')
                    ui.label('Live Log Tail').classes(theme.section_title())
                with ui.row().classes('items-center gap-2'):
                    ui.toggle(
                        {'volttron.log': 'VOLTTRON', 'driver.log': 'Driver'},
                        value=active_log_name,
                        on_change=handle_log_selection,
                    ).props('dense no-caps toggle-color="primary"')
                    log_follow_switch = ui.switch('Follow', value=True, on_change=lambda e: refresh_log() if getattr(e, 'value', False) else None).props('dense color="positive"')
                    refresh_log_btn = ui.button(icon='refresh', on_click=refresh_log).props('flat round').tooltip('Refresh log')
                    binding.bind_from(refresh_log_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    ui.button('Clear Log', icon='delete_sweep', on_click=handle_clear_log).props('flat color="negative"').classes('font-bold')
            log_container = ui.column().classes('w-full')
            with log_container:
                log_view = ui.log(max_lines=1000).classes('w-full h-96 border rounded-md font-mono text-sm p-2')
            
            async def live_refresh_log():
                if log_follow_switch is not None and log_follow_switch.value:
                    await refresh_log()
                    
            ui.timer(0.1, refresh_log, once=True)
            if instance.get('is_local', True):
                ui.timer(3.0, live_refresh_log)

        # Error Log Container
        error_log_container = ui.column().classes('w-full max-w-6xl mt-5 p-4 border border-negative rounded-md')
        error_log_container.visible = False

        with ui.dialog() as install_dialog, ui.card().classes('p-6 gap-4 w-full max-w-xl'):
            ui.label('Install Agent').classes('text-xl font-bold')
            ui.label('Install from a PyPI package, local agent directory, wheel, or git URL.').classes(theme.muted())
            agent_source_input = ui.input('Agent Source', placeholder='volttron-listener or /path/to/agent').props('outlined dense').classes('w-full')
            agent_identity_input = ui.input('VIP Identity', placeholder='listener').props('outlined dense').classes('w-full')
            agent_config_input = ui.input('Agent Config Path', placeholder='Optional path to config file').props('outlined dense').classes('w-full')
            agent_start_switch = ui.switch('Start after install', value=True).props('color="positive"')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=install_dialog.close).props('flat color="gray"')
                ui.button('Install', icon='download', on_click=handle_install_agent).props('color="primary"')

        with ui.dialog() as install_library_dialog, ui.card().classes('p-6 gap-4 w-full max-w-xl'):
            ui.label('Install Library').classes('text-xl font-bold')
            ui.label('Install a VOLTTRON library package into this platform environment.').classes(theme.muted())
            library_source_input = ui.input('Library Source', placeholder='volttron-lib-web or /path/to/library.whl').props('outlined dense').classes('w-full')
            library_force_switch = ui.switch('Force reinstall', value=False).props('color="warning"')
            library_prerelease_switch = ui.switch('Allow prereleases', value=False).props('color="primary"')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=install_library_dialog.close).props('flat color="gray"')
                ui.button('Install Library', icon='download', on_click=handle_install_library).props('color="primary"')
