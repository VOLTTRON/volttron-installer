from nicegui import ui, binding
import io
import json
import zipfile

import src.db as db
from src import ssh_remote
from src import theme
from src.manage_instances import agent_management
from src.manage_instances import config_store
from src.manage_instances.log_parser import parse_volttron_log

CARD_STYLE = (
    'background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 6px; '
    'padding: 1.25rem; box-shadow: var(--card-shadow);'
)
EMPTY_STATE_STYLE = (
    'min-height: 96px; border: 1px dashed var(--border-color); border-radius: 6px; '
    'background: transparent;'
)
LIST_ROW_STYLE = (
    'border-bottom: 1px solid var(--border-color); min-height: 56px; padding: 0.75rem 0;'
)
SUBTLE_ROW_STYLE = (
    'border-bottom: 1px solid var(--border-color); min-height: 48px; padding: 0.55rem 0;'
)

DEFAULT_LIBRARY_NAMES = {
    'volttron-lib-auth',
    'volttron-lib-base-driver',
    'volttron-lib-tree',
    'volttron-lib-web',
    'volttron-lib-zmq',
}


def _uploaded_config_type(filename: str) -> str:
    lower_name = filename.lower()
    if lower_name.endswith(('.json', '.config')):
        return 'application/json'
    if lower_name.endswith('.csv'):
        return 'text/csv'
    return 'text/plain'


def _uploaded_config_name(filename: str, agent_identity: str) -> str:
    clean_name = filename.replace('\\', '/').split('/')[-1]
    lower_name = clean_name.lower()
    if agent_identity == 'platform.driver' and lower_name.endswith('.config'):
        return f"devices/{clean_name.rsplit('.', 1)[0]}"
    return clean_name


def _uploaded_config_entries(filename: str, content: bytes, agent_identity: str) -> list[tuple[str, str, str]]:
    lower_name = filename.lower()
    if lower_name.endswith('.zip'):
        entries: list[tuple[str, str, str]] = []
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                member_name = member.filename.replace('\\', '/').split('/')[-1]
                if not member_name or member_name.lower().endswith('readme.txt'):
                    continue
                content_type = _uploaded_config_type(member_name)
                if content_type not in {'application/json', 'text/csv', 'text/plain'}:
                    continue
                text = archive.read(member).decode('utf-8-sig')
                entries.append((_uploaded_config_name(member_name, agent_identity), text, content_type))
        return entries

    return [(
        _uploaded_config_name(filename, agent_identity),
        content.decode('utf-8-sig'),
        _uploaded_config_type(filename),
    )]

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
    last_log_content = None
    last_agents_signature = None
    last_libraries_signature = None
    agent_refresh_in_progress = False
    library_refresh_in_progress = False
    ssh_refresh_in_progress = False

    def remote_password_needed() -> bool:
        return ssh_remote.needs_key(instance)

    def render_log_entries(content: str) -> None:
        if log_view is None:
            return

        level_colors = {
            "ERROR": ("#fee2e2", "#b91c1c", "#fecaca"),
            "CRITICAL": ("#fee2e2", "#991b1b", "#fca5a5"),
            "WARNING": ("#fef3c7", "#92400e", "#fde68a"),
            "INFO": ("#dbeafe", "#1d4ed8", "#bfdbfe"),
            "DEBUG": ("#e5e7eb", "#374151", "#d1d5db"),
            "TEXT": ("#e5e7eb", "#374151", "#d1d5db"),
        }

        entries = parse_volttron_log(content)
        log_view.clear()
        with log_view:
            if not entries:
                ui.label("Log is empty.").style("color: var(--text-muted); padding: 0.75rem;")
                return

            for entry in entries:
                bg, fg, border = level_colors.get(entry.level, level_colors["TEXT"])
                with ui.row().classes("w-full no-wrap items-start gap-2").style(
                    "border-bottom: 1px solid var(--border-color); padding: 0.45rem 0.65rem;"
                ):
                    ui.label(entry.level).style(
                        f"width: 4.7rem; min-width: 4.7rem; text-align: center; font-size: 0.72rem; "
                        f"font-weight: 800; color: {fg}; background: {bg}; border: 1px solid {border}; "
                        "border-radius: 4px; padding: 0.12rem 0.25rem; line-height: 1.35;"
                    )
                    ui.label(entry.timestamp or "-").style(
                        "width: 11.2rem; min-width: 11.2rem; color: var(--text-muted); "
                        "font-family: monospace; font-size: 0.78rem; line-height: 1.5;"
                    )
                    source = f"{entry.logger}:{entry.source_line}" if entry.logger else ""
                    ui.label(source).style(
                        "width: 18rem; min-width: 18rem; color: var(--text-muted); "
                        "font-family: monospace; font-size: 0.78rem; line-height: 1.5; overflow-wrap: anywhere;"
                    )
                    ui.label(entry.message).classes("flex-grow").style(
                        "color: var(--text-color); font-family: monospace; font-size: 0.82rem; "
                        "line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere;"
                    )

    def render_ssh_needed(container, message: str):
        container.clear()
        with container:
            with ui.column().classes('w-full items-center justify-center gap-2').style(EMPTY_STATE_STYLE):
                ui.icon('key', size='sm', color='gray')
                ui.label(message).style('color: #9ca3af;')

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
        error_log_container.style('display: flex;')
        stdout = getattr(error, 'stdout', '')
        stderr = getattr(error, 'stderr', '')
        details = f"{error}\n\n"
        if stderr:
            details += f"stderr:\n{stderr}\n"
        if stdout:
            details += f"stdout:\n{stdout}\n"
        with error_log_container:
            ui.label(title).classes('text-red-500 font-bold text-lg mb-2')
            ui.code(details).classes('w-full').style('background: var(--code-bg); color: #ef4444; border: 1px solid #ef4444; white-space: pre-wrap;')

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
                with ui.column().classes('w-full items-center justify-center gap-2').style(EMPTY_STATE_STYLE):
                    ui.icon('power_settings_new', size='sm', color='gray')
                    ui.label('Start VOLTTRON to view installed agents.').style('color: #9ca3af;')
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
                with ui.column().classes('w-full items-center justify-center gap-2').style(EMPTY_STATE_STYLE):
                    ui.icon('error_outline', size='md', color='red')
                    ui.label(f'Could not load agents: {e}').style('color: #f87171;')
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
                with ui.column().classes('w-full items-center justify-center gap-2').style(EMPTY_STATE_STYLE):
                    ui.icon('extension_off', size='sm', color='gray')
                    ui.label('No agents installed').style('color: #9ca3af;')
                return

            for agent in agents:
                agent_id = agent.get('uuid') or agent.get('identity')
                agent_identity = agent.get('identity', 'unknown')
                is_running = agent.get('state') == 'running'
                with ui.row().classes('w-full items-center justify-between gap-4').style(LIST_ROW_STYLE):
                    with ui.column().classes('gap-1'):
                        with ui.row().classes('items-center gap-2'):
                            ui.label(agent_identity).style('color: #f3f4f6; font-weight: 700;')
                            ui.badge('running' if is_running else 'stopped', color='positive' if is_running else 'gray')
                        detail = agent.get('status') or agent.get('uuid') or 'No status detail'
                        ui.label(detail).style('color: #9ca3af; font-size: 0.8rem;')
                        if agent.get('health'):
                            ui.label(agent.get('health')).style('color: #a7f3d0; font-size: 0.8rem;')

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

                    async def do_remove(agent_ref=agent_id):
                        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color);'):
                            ui.label(f'Remove {agent.get("identity", agent_ref)}?').classes('text-lg font-bold')
                            ui.label('This uninstalls the agent from the running platform.').style('color: var(--text-muted);')
                            with ui.row().classes('justify-end w-full gap-2'):
                                ui.button('Cancel', on_click=confirm_dialog.close).props('flat color="gray"')
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

                    async def open_config_store(agent_ref=agent_identity):
                        selected_config = None
                        config_names_container = None
                        config_name_input = None
                        config_type_select = None
                        config_content_input = None
                        save_button = None
                        delete_button = None
                        status_label = None

                        async def load_configs():
                            if config_names_container is None:
                                return
                            config_names_container.clear()
                            try:
                                names = await config_store.list_configs(instance, agent_ref)
                            except Exception as e:
                                with config_names_container:
                                    ui.label(f'Could not load configs: {e}').style('color: #f87171;')
                                return

                            with config_names_container:
                                if not names:
                                    ui.label('No configs stored for this agent.').style('color: #9ca3af;')
                                    return

                                for name in names:
                                    async def select_config(config_name=name):
                                        nonlocal selected_config
                                        selected_config = config_name
                                        try:
                                            content, content_type = await config_store.get_config(instance, agent_ref, config_name)
                                            config_name_input.value = config_name
                                            config_type_select.value = content_type if content_type in ['application/json', 'text/csv', 'text/plain'] else 'application/json'
                                            config_content_input.value = content
                                            delete_button.enable()
                                            save_button.set_text('Update Config')
                                            status_label.set_text(f'Editing {config_name}')
                                        except Exception as e:
                                            ui.notify(f'Failed to load config: {e}', type='negative')

                                    ui.button(name, icon='description', on_click=select_config).props('flat color="white" align="left"').classes('w-full justify-start')

                        def clear_editor():
                            nonlocal selected_config
                            selected_config = None
                            config_name_input.value = ''
                            config_type_select.value = 'application/json'
                            config_content_input.value = '{}'
                            delete_button.disable()
                            save_button.set_text('Create Config')
                            status_label.set_text('Creating new config')

                        async def save_config():
                            overwrite = selected_config == (config_name_input.value or '').strip()
                            try:
                                await config_store.save_config(
                                    instance,
                                    agent_ref,
                                    (config_name_input.value or '').strip(),
                                    config_content_input.value or '',
                                    config_type_select.value,
                                    overwrite=overwrite,
                                )
                                ui.notify('Config saved', type='positive')
                                await load_configs()
                            except Exception as e:
                                ui.notify(f'Failed to save config: {e}', type='negative')

                        async def upload_config_file(event):
                            try:
                                content = await event.file.read()
                                entries = _uploaded_config_entries(event.file.name, content, agent_ref)
                                if not entries:
                                    ui.notify('No supported config files found in upload', type='warning')
                                    return

                                for config_name, config_content, content_type in entries:
                                    await config_store.save_config(
                                        instance,
                                        agent_ref,
                                        config_name,
                                        config_content,
                                        content_type,
                                        overwrite=True,
                                    )

                                ui.notify(f'Uploaded {len(entries)} config entr{"y" if len(entries) == 1 else "ies"}', type='positive')
                                await load_configs()
                            except Exception as e:
                                ui.notify(f'Failed to upload config: {e}', type='negative')

                        async def delete_selected_config():
                            nonlocal selected_config
                            if not selected_config:
                                return
                            try:
                                await config_store.delete_config(instance, agent_ref, selected_config)
                                ui.notify(f'Deleted {selected_config}', type='positive')
                                clear_editor()
                                await load_configs()
                            except Exception as e:
                                ui.notify(f'Failed to delete config: {e}', type='negative')

                        async def delete_all_agent_configs():
                            with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color);'):
                                ui.label(f'Delete all configs for {agent_ref}?').classes('text-lg font-bold text-red-400')
                                ui.label('This removes every configuration entry for this agent from the VOLTTRON config store.').style('color: var(--text-muted);')
                                with ui.row().classes('justify-end w-full gap-2'):
                                    ui.button('Cancel', on_click=confirm_dialog.close).props('flat color="gray"')
                                    async def confirm_delete_all():
                                        confirm_dialog.close()
                                        try:
                                            await config_store.delete_all_configs(instance, agent_ref)
                                            ui.notify('All configs deleted', type='positive')
                                            clear_editor()
                                            await load_configs()
                                        except Exception as e:
                                            ui.notify(f'Failed to delete configs: {e}', type='negative')
                                    ui.button('Delete All', icon='delete_sweep', on_click=confirm_delete_all).props('color="negative"')
                            confirm_dialog.open()

                        with ui.dialog() as config_dialog:
                            with ui.card().classes('p-0').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); width: 94vw; height: 90vh; max-width: none; max-height: none; display: flex; flex-direction: column;'):
                              with ui.row().classes('w-full items-center justify-between p-5').style('border-bottom: 1px solid var(--border-color); flex: 0 0 auto;'):
                                with ui.column().classes('gap-1'):
                                    ui.label('Config Store').classes('text-xl font-bold')
                                    ui.label(agent_ref).style('color: var(--text-muted);')
                                close_btn = ui.button(icon='close', on_click=config_dialog.close).props('flat round')
                                binding.bind_from(close_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')

                              with ui.row().classes('w-full gap-0 items-stretch no-wrap').style('flex: 1 1 auto; min-height: 0;'):
                                with ui.column().classes('gap-3 p-4').style('width: 320px; min-width: 320px; border-right: 1px solid var(--border-color); min-height: 0;'):
                                    ui.button('New Config', icon='add', on_click=clear_editor).props('color="primary" unelevated').classes('w-full')
                                    ui.upload(
                                        label='Upload Config',
                                        auto_upload=True,
                                        multiple=True,
                                        on_upload=upload_config_file,
                                    ).props('accept=".json,.config,.csv,.txt,.zip" color="primary" flat bordered').classes('w-full')
                                    with ui.row().classes('w-full justify-between items-center'):
                                        ui.label('Stored Configs').style('font-weight: 700;')
                                    config_names_container = ui.column().classes('w-full gap-1').style('flex: 1 1 auto; min-height: 0; overflow: auto;')
                                    ui.button('Delete All Configs', icon='delete_sweep', on_click=delete_all_agent_configs).props('outline color="negative"').classes('w-full')

                                with ui.column().classes('gap-3 p-5 flex-grow').style('min-width: 0; min-height: 0;'):
                                    status_label = ui.label('Creating new config').style('color: var(--text-muted);')
                                    with ui.row().classes('w-full gap-3 no-wrap'):
                                        config_name_input = ui.input('Config Name', placeholder='e.g. devices/campus/building/fake').props('outlined dense').classes('flex-grow')
                                        config_type_select = ui.select(
                                            {
                                                'application/json': 'JSON',
                                                'text/csv': 'CSV',
                                                'text/plain': 'Raw Text',
                                            },
                                            value='application/json',
                                            label='Content Type',
                                        ).props('outlined dense').style('width: 180px;')
                                    ui.label('Note: Device configurations for drivers typically require the "devices/" prefix.').style('color: var(--text-muted); font-size: 0.75rem; margin-top: -0.25rem;')
                                    config_content_input = ui.textarea('Content', value='{}').props('outlined').classes('w-full').style('flex: 1 1 auto; min-height: 0; font-family: monospace;')
                                    with ui.row().classes('w-full justify-end gap-2'):
                                        delete_button = ui.button('Delete Config', icon='delete', on_click=delete_selected_config).props('outline color="negative"')
                                        save_button = ui.button('Create Config', icon='save', on_click=save_config).props('color="primary"')
                                    delete_button.disable()

                        config_dialog.open()
                        await load_configs()

                    with ui.row().classes('items-center gap-1'):
                        ui.button(icon='settings', on_click=open_config_store).props('flat round color="primary"').tooltip('Config store')
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
                with ui.column().classes('w-full items-center justify-center gap-2').style(EMPTY_STATE_STYLE):
                    ui.icon('error_outline', size='md', color='red')
                    ui.label(f'Could not load libraries: {e}').style('color: #f87171;')
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
                with ui.column().classes('w-full items-center justify-center gap-2').style(EMPTY_STATE_STYLE):
                    ui.icon('inventory_2', size='sm', color='gray')
                    ui.label('No VOLTTRON libraries installed').style('color: var(--text-muted);')
                return

            def render_library_row(library: dict, removable: bool = True):
                library_name = library.get('name', 'unknown')
                library_version = library.get('version') or 'unknown version'

                async def do_remove_library(lib_name=library_name):
                    with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color);'):
                        ui.label(f'Remove {lib_name}?').classes('text-lg font-bold')
                        ui.label('This removes the library package from the selected platform environment. Agents that depend on it may stop working.').style('color: var(--text-muted);')
                        with ui.row().classes('justify-end w-full gap-2'):
                            ui.button('Cancel', on_click=confirm_dialog.close).props('flat color="gray"')
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

                row_style = LIST_ROW_STYLE if removable else SUBTLE_ROW_STYLE
                with ui.row().classes('w-full items-center justify-between gap-4').style(row_style):
                    with ui.column().classes('gap-1'):
                        ui.label(library_name).style('color: var(--text-color); font-weight: 700;')
                        ui.label(library_version).style('color: var(--text-muted); font-size: 0.8rem;')
                    if removable:
                        ui.button(icon='delete', on_click=do_remove_library).props('flat round color="negative"').tooltip('Remove library').set_enabled(current_platform_state == 'running')

            if additional_libraries:
                for library in additional_libraries:
                    render_library_row(library)
            else:
                with ui.column().classes('w-full items-center justify-center gap-2').style(EMPTY_STATE_STYLE):
                    ui.icon('extension_off', size='sm', color='gray')
                    ui.label('No additional VOLTTRON libraries installed').style('color: var(--text-muted);')

            if default_libraries:
                default_margin = 'margin-top: 0.75rem;' if additional_libraries else ''
                with ui.expansion(f'Default Libraries ({len(default_libraries)})', icon='inventory_2').classes('w-full').style(f'{default_margin} color: var(--text-color);'):
                    with ui.column().classes('w-full gap-0 pl-8 pr-1'):
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
                content = await agent_management.read_log_tail(instance, 300)
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
        if log_follow_switch is not None and log_follow_switch.value:
            ui.run_javascript(
                f'''
                setTimeout(() => {{
                    const el = getElement("{log_view.id}");
                    if (el) el.scrollTop = el.scrollHeight;
                }}, 0);
                '''
            )

    async def handle_clear_log():
        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color);'):
            ui.label('Clear volttron.log?').classes('text-lg font-bold')
            ui.label('This truncates the current log file for this instance. New log entries will still appear here.').style('color: var(--text-muted);')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=confirm_dialog.close).props('flat color="gray"')

                async def confirm_clear():
                    nonlocal last_log_content
                    confirm_dialog.close()
                    try:
                        await agent_management.clear_log(instance)
                        last_log_content = None
                        await refresh_log()
                        ui.notify('Log cleared', type='positive')
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
        with ui.dialog() as progress_dialog, ui.card().classes('p-8 items-center gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 12px;'):
            ui.label('Installing Agent').classes('text-xl font-bold')
            ui.spinner(size='lg')
            ui.label(source).style('color: var(--text-muted);')
        progress_dialog.open()
        try:
            await agent_management.install_agent(instance, source, identity, start, config)
            progress_dialog.close()
            ui.notify('Agent installed successfully', type='positive')
            error_log_container.style('display: none;')
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
        with ui.dialog() as progress_dialog, ui.card().classes('p-8 items-center gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 12px;'):
            ui.label('Installing Library').classes('text-xl font-bold')
            ui.spinner(size='lg')
            ui.label(source).style('color: var(--text-muted);')
        progress_dialog.open()
        try:
            await agent_management.install_library(instance, source, force, allow_prerelease)
            progress_dialog.close()
            ui.notify('Library installed successfully', type='positive')
            error_log_container.style('display: none;')
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
                error_log_container.style('display: none;')
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
                    with ui.dialog() as sudo_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); min-width: 420px;'):
                        ui.label('Sudo Password Required').classes('text-lg font-bold')
                        ui.label(f'Stopping {instance_name} uses systemd and needs sudo on this machine. The password is used once and is not saved.').style('color: var(--text-muted);')
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

        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color);'):
            ui.label(f'Shut down {instance_name}?').classes('text-lg font-bold')
            ui.label('This stops the selected platform. Ansible deployments use the systemd service.').style('color: var(--text-muted);')
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
        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); min-width: 520px;'):
            ui.label(f'Delete {instance_name}?').classes('text-lg font-bold text-red-400')
            ui.label('This will shut down the platform, delete its virtual environment, delete VOLTTRON_HOME, and remove it from this installer.').style('color: var(--text-muted);')
            with ui.column().classes('w-full gap-1 p-3').style('background: var(--code-bg); border: 1px solid var(--border-color); border-radius: 6px;'):
                ui.label(f'Virtual Env: {venv_path}').style('color: var(--text-muted); font-size: 0.85rem;')
                ui.label(f'VOLTTRON Home: {volttron_home}').style('color: var(--text-muted); font-size: 0.85rem;')
                ui.label(f'Instance Record: instances_data/{instance_name}.json').style('color: var(--text-muted); font-size: 0.85rem;')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=confirm_dialog.close).props('flat color="gray"')

                async def confirm_delete():
                    confirm_dialog.close()
                    with ui.dialog() as progress_dialog, ui.card().classes('p-8 items-center gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 12px;'):
                        ui.label('Deleting Platform').classes('text-xl font-bold')
                        ui.spinner(size='lg')
                        ui.label(instance_name).style('color: var(--text-muted);')
                    progress_dialog.open()
                    try:
                        messages = await agent_management.delete_platform_files(instance)
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

    with ui.column().classes('w-full items-center py-8').style('min-height: 100vh; background: var(--bg-color);'):
        # Header
        with ui.column().classes('w-full max-w-6xl gap-4 mb-8'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-3'):
                    back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/instances')).props('flat round')
                    binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    ui.label(instance_name).style('font-size: 2rem; font-weight: 700; color: var(--text-color);')
                
                with ui.row().classes('items-center gap-3'):
                    status_badge = ui.badge('Checking Status...', color='gray').style('font-size: 0.95rem; padding: 0.45rem 0.75rem;')
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
                    with ui.dialog() as dialog, ui.card().classes('p-8 items-center gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 12px;'):
                        ui.label('Starting Platform').classes('text-xl font-bold')
                        ui.spinner(size='lg')
                        ui.label('Waiting for initialization...')
                    dialog.open()

                    try:
                        await start_platform_command(instance.get('venv'), instance.get('volttron_home'), instance, sudo_password=sudo_password)
                        dialog.close()
                        ui.notify(f'{instance_name} started successfully!', type='positive')
                        error_log_container.clear()
                        error_log_container.style('display: none;')
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
                            with ui.dialog() as sudo_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); min-width: 420px;'):
                                ui.label('Sudo Password Required').classes('text-lg font-bold')
                                ui.label(f'Starting {instance_name} uses systemd and needs sudo on this machine. The password is used once and is not saved.').style('color: var(--text-muted);')
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
                        error_log_container.style('display: flex;')
                        with error_log_container:
                            ui.label('Startup Error (Last 20 lines of volttron.log)').classes('text-red-500 font-bold text-lg mb-2')
                            ui.code(log_content).classes('w-full').style('background: var(--code-bg); color: #f87171; border: 1px solid #ef4444;')

                await run_start()

            with ui.row().classes('gap-2 items-center'):
                start_button = ui.button('Start', icon='play_arrow', on_click=handle_start).props('color="positive" unelevated').style('font-weight: 600; min-width: 112px;')
                shutdown_button = ui.button('Shut Down', icon='power_settings_new', on_click=handle_shutdown).props('outline color="negative"').style('font-weight: 600; min-width: 128px;')
                ui.button('Delete', icon='delete_forever', on_click=handle_delete_platform).props('flat color="negative"').style('font-weight: 600; min-width: 104px;')
                start_button.disable()
                shutdown_button.disable()

        with ui.row().classes('w-full max-w-6xl gap-5 items-stretch'):
            # Configuration Card
            with ui.card().classes('w-full max-w-md').style(CARD_STYLE):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('settings', size='sm', color='#6366f1')
                    ui.label('Configuration').style('font-size: 1.2rem; font-weight: bold; color: var(--text-color);')
                
                ui.separator().classes('mb-4')
                
                with ui.column().classes('gap-3 w-full'):
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
                                        textarea.style.position = 'fixed';
                                        textarea.style.left = '-9999px';
                                        textarea.style.top = '0';
                                        document.body.appendChild(textarea);
                                        textarea.focus();
                                        textarea.select();
                                        document.execCommand('copy');
                                        document.body.removeChild(textarea);
                                    }}
                                }} catch (error) {{
                                    const textarea = document.createElement('textarea');
                                    textarea.value = text;
                                    textarea.style.position = 'fixed';
                                    textarea.style.left = '-9999px';
                                    textarea.style.top = '0';
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
                        with ui.row().classes('w-full justify-between items-center gap-3 no-wrap'):
                            ui.label(key).style('color: var(--text-muted); font-size: 0.9rem;')
                            with ui.row().classes('items-center gap-1 no-wrap').style('min-width: 0;'):
                                ui.label(value).style('color: var(--text-color); font-weight: 500; overflow-wrap: anywhere;')
                                if copy_command:
                                    copy_button(copy_command, copy_label or key)
                    
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
                        ui.separator().classes('my-2')
                        row_label('SSH User', instance.get('ssh_username', 'N/A'))
                        row_label('SSH Port', str(instance.get('ssh_port', '22')))
                        row_label('SSH Key', instance.get('ssh_key_path') or 'Agent/default keys')
                        ui.label('Remote management uses SSH keys only.').style('color: var(--text-muted); font-size: 0.8rem;')
            
            # Agents Card
            with ui.card().classes('flex-grow').style(CARD_STYLE + 'min-width: 420px;'):
                with ui.row().classes('items-center gap-2 mb-4 justify-between w-full'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('smart_toy', size='sm', color='#ec4899')
                        ui.label('Installed Agents').style('font-size: 1.2rem; font-weight: bold; color: var(--text-color);')
                    
                    install_agent_button = ui.button('Install Agent', icon='add', on_click=lambda: install_dialog.open()).props('outline color="primary"').style('font-weight: 700; min-width: 148px;')
                    install_agent_button.disable()
                
                ui.separator().classes('mb-4')
                
                agents_container = ui.column().classes('w-full gap-0').style('min-height: 120px;')
                ui.timer(0.2, refresh_agents, once=True)
                if instance.get('is_local', True):
                    ui.timer(8.0, refresh_agents)

        with ui.card().classes('w-full max-w-6xl mt-5').style(CARD_STYLE):
            with ui.row().classes('items-center gap-2 mb-4 justify-between w-full'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('extension', size='sm', color='#f59e0b')
                    ui.label('Installed Libraries').style('font-size: 1.2rem; font-weight: bold; color: var(--text-color);')

                with ui.row().classes('items-center gap-2'):
                    refresh_lib_btn = ui.button(icon='refresh', on_click=refresh_libraries).props('flat round').tooltip('Refresh libraries')
                    binding.bind_from(refresh_lib_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    install_library_button = ui.button('Install Library', icon='add', on_click=lambda: install_library_dialog.open()).props('outline color="primary"').style('font-weight: 700; min-width: 156px;')
                    install_library_button.disable()

            ui.separator().classes('mb-4')

            libraries_container = ui.column().classes('w-full gap-0').style('min-height: 120px;')
            ui.timer(0.4, refresh_libraries, once=True)
            if instance.get('is_local', True):
                ui.timer(20.0, refresh_libraries)

        with ui.card().classes('w-full max-w-6xl mt-5').style(CARD_STYLE):
            with ui.row().classes('items-center justify-between w-full mb-4'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('article', size='sm', color='#10b981')
                    ui.label('Live Log Tail').style('font-size: 1.2rem; font-weight: bold; color: var(--text-color);')
                with ui.row().classes('items-center gap-2'):
                    log_follow_switch = ui.switch('Follow', value=True).props('dense color="positive"')
                    refresh_log_btn = ui.button(icon='refresh', on_click=refresh_log).props('flat round').tooltip('Refresh log')
                    binding.bind_from(refresh_log_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    ui.button('Clear Log', icon='delete_sweep', on_click=handle_clear_log).props('flat color="negative"').style('font-weight: 700;')
            log_container = ui.column().classes('w-full')
            with log_container:
                log_view = ui.column().classes('w-full gap-0').style(
                    'height: 420px; overflow-y: auto; background: var(--code-bg); '
                    'border: 1px solid var(--code-border); border-radius: 6px; color: var(--text-color);'
                )
            ui.timer(0.1, refresh_log, once=True)
            if instance.get('is_local', True):
                ui.timer(3.0, refresh_log)

        # Error Log Container
        error_log_container = ui.column().classes('w-full max-w-6xl mt-5 p-4').style('display: none; background: var(--card-bg); border: 1px solid rgba(239, 68, 68, 0.5); border-radius: 8px;')

        with ui.dialog() as install_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 12px; min-width: 520px;'):
            ui.label('Install Agent').classes('text-xl font-bold')
            ui.label('Install from a PyPI package, local agent directory, wheel, or git URL.').style('color: var(--text-muted);')
            agent_source_input = ui.input('Agent Source', placeholder='volttron-listener or /path/to/agent').props('outlined dense').classes('w-full')
            agent_identity_input = ui.input('VIP Identity', placeholder='listener').props('outlined dense').classes('w-full')
            agent_config_input = ui.input('Agent Config Path', placeholder='Optional path to config file').props('outlined dense').classes('w-full')
            agent_start_switch = ui.switch('Start after install', value=True).props('color="positive"')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=install_dialog.close).props('flat color="gray"')
                ui.button('Install', icon='download', on_click=handle_install_agent).props('color="primary"')

        with ui.dialog() as install_library_dialog, ui.card().classes('p-6 gap-4').style('background: var(--dialog-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 12px; min-width: 520px;'):
            ui.label('Install Library').classes('text-xl font-bold')
            ui.label('Install a VOLTTRON library package into this platform environment.').style('color: var(--text-muted);')
            library_source_input = ui.input('Library Source', placeholder='volttron-lib-web or /path/to/library.whl').props('outlined dense').classes('w-full')
            library_force_switch = ui.switch('Force reinstall', value=False).props('color="warning"')
            library_prerelease_switch = ui.switch('Allow prereleases', value=False).props('color="primary"')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=install_library_dialog.close).props('flat color="gray"')
                ui.button('Install Library', icon='download', on_click=handle_install_library).props('color="primary"')
