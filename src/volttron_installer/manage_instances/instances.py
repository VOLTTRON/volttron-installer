import asyncio

from nicegui import ui, app
from volttron_installer.dark import dark_mode_control
import volttron_installer.db as db
from volttron_installer.manage_instances import agent_management
from volttron_installer.manage_instances.status_check import check_volttron_rest_status
from volttron_installer.manage_instances.start_platform import start_platform_command

def render():
    dark = dark_mode_control()
    instances = db.get_instances()
    view_mode = app.storage.user.get('instances_view_mode', 'cards')
    status_results = {
        instance.get('name', ''): {'status': 'checking', 'message': 'Checking platform status'}
        for instance in instances
    }
    status_badges = {}

    def machine_key(instance: dict) -> str:
        if instance.get('is_local', True):
            return 'local'
        return (instance.get('host') or 'unknown remote host').strip().lower()

    def grouped_instances() -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = {}
        for instance in instances:
            groups.setdefault(machine_key(instance), []).append(instance)
        return groups

    def machine_details(key: str, machine_instances: list[dict]) -> tuple[str, str, str]:
        count = len(machine_instances)
        if key == 'local':
            return 'Local machine', f'localhost · {count} instance{"s" if count != 1 else ""}', 'computer'
        host = machine_instances[0].get('host') or key
        return host, f'Remote machine · {count} instance{"s" if count != 1 else ""}', 'dns'

    def status_presentation(result: dict) -> tuple[str, str]:
        status = result.get('status', 'unknown')
        return {
            'checking': ('Checking...', 'gray'),
            'running': ('Running', 'positive'),
            'stopped': ('Stopped', 'negative'),
            'degraded': ('Web Offline', 'warning'),
            'unknown': ('Unknown', 'gray'),
        }.get(status, ('Unknown', 'gray'))

    async def refresh_instance_status(instance: dict):
        instance_name = instance.get('name', '')
        try:
            result = await check_volttron_rest_status(instance)
        except Exception as error:
            result = {'status': 'unknown', 'message': str(error)}
        status_results[instance_name] = result
        badge = status_badges.get(instance_name)
        if badge is not None:
            label, color = status_presentation(result)
            badge.set_text(label)
            badge._props['color'] = color
            badge.update()

    async def refresh_all_statuses():
        await asyncio.gather(*(refresh_instance_status(instance) for instance in instances))

    async def run_instance_action(instance: dict, action_name: str, action, sudo_password: str = ''):
        instance_name = instance.get('name', 'instance')
        with ui.dialog() as progress_dialog, ui.card().classes('p-8 items-center gap-4'):
            ui.label(f'{action_name} {instance_name}').classes('text-xl font-bold')
            ui.spinner(size='lg')
        progress_dialog.open()
        try:
            await action(sudo_password)
            progress_dialog.close()
            ui.notify(f'{instance_name}: {action_name.lower()} complete', type='positive')
            await refresh_instance_status(instance)
        except Exception as error:
            progress_dialog.close()
            ui.notify(f'{action_name} failed: {error}', type='negative')

    def request_sudo(instance: dict, action_name: str, action, button_icon: str, button_color: str):
        with ui.dialog() as sudo_dialog, ui.card().classes('p-6 gap-4 w-full max-w-lg'):
            ui.label(f'{action_name} {instance.get("name", "instance")}').classes('text-lg font-bold')
            ui.label('Local systemd access requires sudo. The password is used once and is not saved.').classes('text-grey-6')
            password_input = ui.input('Local sudo password', password=True, password_toggle_button=True).props(
                'outlined autocomplete="current-password"'
            ).classes('w-full')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=sudo_dialog.close).props('flat color="gray"')

                async def confirm():
                    password = password_input.value or ''
                    if not password:
                        ui.notify('Enter your sudo password.', type='warning')
                        return
                    sudo_dialog.close()
                    await run_instance_action(instance, action_name, action, password)

                ui.button(action_name, icon=button_icon, on_click=confirm).props(f'color="{button_color}"')
        sudo_dialog.open()

    def render_instance_menu(instance: dict):
        instance_name = instance.get('name', '')
        is_local = instance.get('is_local', True)
        uses_systemd = instance.get('deployment_method') == 'ansible'

        async def start(sudo_password: str = ''):
            await start_platform_command(
                instance.get('venv'),
                instance.get('volttron_home'),
                instance,
                sudo_password=sudo_password,
            )

        async def stop(sudo_password: str = ''):
            await agent_management.shutdown_platform(instance, sudo_password=sudo_password)

        async def delete(sudo_password: str = ''):
            await agent_management.delete_platform_files(instance, sudo_password=sudo_password)
            db.delete_instance(instance_name)
            ui.navigate.to('/instances')

        async def handle_start():
            if is_local and uses_systemd:
                request_sudo(instance, 'Start', start, 'play_arrow', 'positive')
            else:
                await run_instance_action(instance, 'Start', start)

        async def handle_stop():
            if is_local and uses_systemd:
                request_sudo(instance, 'Stop', stop, 'stop', 'negative')
            else:
                await run_instance_action(instance, 'Stop', stop)

        def handle_delete():
            with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4 w-full max-w-lg'):
                ui.label(f'Delete {instance_name}?').classes('text-lg font-bold')
                ui.label('This removes the systemd service, virtual environment, VOLTTRON_HOME, and installer record.').classes('text-grey-6')
                with ui.row().classes('justify-end w-full gap-2'):
                    ui.button('Cancel', on_click=confirm_dialog.close).props('flat color="gray"')

                    async def confirm():
                        confirm_dialog.close()
                        if is_local:
                            request_sudo(instance, 'Delete', delete, 'delete_forever', 'negative')
                        else:
                            await run_instance_action(instance, 'Delete', delete)

                    ui.button('Delete', icon='delete_forever', on_click=confirm).props('color="negative"')
            confirm_dialog.open()

        with ui.button(icon='more_vert').props('flat round color="gray"').tooltip('Instance actions'):
            with ui.menu():
                ui.menu_item('Manage', on_click=lambda: ui.navigate.to(f'/manage/{instance_name}'))
                ui.menu_item('Copy', on_click=lambda: ui.navigate.to(f'/deploy/copy/{instance_name}'))
                ui.menu_item('Start', on_click=handle_start)
                ui.menu_item('Stop', on_click=handle_stop)
                ui.separator()
                ui.menu_item('Delete', on_click=handle_delete)

    def render_status(instance: dict):
        instance_name = instance.get('name', '')
        label, color = status_presentation(status_results.get(instance_name, {}))
        badge = ui.badge(label, color=color)
        status_badges[instance_name] = badge
        return badge

    def render_card(instance: dict):
        with ui.card().classes('w-full p-6 h-full gap-4'):
            with ui.row().classes('w-full justify-between items-start'):
                with ui.column().classes('gap-1'):
                    ui.label(instance.get('name', 'Unknown')).classes('text-xl font-semibold')
                    ui.label(instance.get('type', 'Unknown Type')).classes('text-xs text-grey-6 uppercase font-medium')
                render_status(instance)

            ui.separator()

            with ui.column().classes('w-full gap-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('dns', size='sm', color='gray')
                    ui.label(instance.get('host', 'localhost') if not instance.get('is_local') else 'localhost')
                with ui.row().classes('items-center gap-2'):
                    ui.icon('link', size='sm', color='gray')
                    ui.label(instance.get('vip') or 'VIP address not recorded').classes('text-grey-6 text-sm')
                with ui.row().classes('items-center gap-2'):
                    ui.icon('language', size='sm', color='gray')
                    ui.label(instance.get('web_bind_address') or 'Web interface disabled').classes('text-grey-6 text-sm')

            with ui.row().classes('w-full gap-2'):
                ui.button(
                    'Manage',
                    on_click=lambda instance_name=instance.get('name'): ui.navigate.to(f'/manage/{instance_name}'),
                ).props('color="primary" rounded flex-grow')
                render_instance_menu(instance)

    def render_list_item(instance: dict):
        host = instance.get('host', 'localhost') if not instance.get('is_local') else 'localhost'
        instance_name = instance.get('name', 'Unknown')
        host_type = instance.get('type', 'Modular')
        with ui.item(on_click=lambda n=instance_name: ui.navigate.to(f'/manage/{n}')).classes('rounded').props('clickable v-ripple'):
            with ui.item_section().props('avatar'):
                ui.icon('dns', color='primary')
            with ui.item_section():
                ui.item_label(instance_name).classes('font-semibold')
                ui.item_label(f'{host_type} · {host}').props('caption')
            with ui.item_section():
                ui.item_label(instance.get('vip') or '—').classes('font-mono text-sm')
                ui.item_label(instance.get('web_bind_address') or '—').props('caption').classes('font-mono')
            with ui.item_section().props('side'):
                render_status(instance)
            with ui.item_section().props('side'):
                ui.element('div').on('click.stop', lambda: None)
                render_instance_menu(instance)

    @ui.refreshable
    def render_instances():
        status_badges.clear()
        max_width = 'max-w-5xl' if view_mode == 'list' else 'max-w-6xl'
        with ui.column().classes(f'w-full {max_width} gap-4'):
            for key, machine_instances in grouped_instances().items():
                label, caption, icon = machine_details(key, machine_instances)
                with ui.expansion(label, caption=caption, icon=icon, value=True).classes('w-full').props('bordered'):
                    if view_mode == 'list':
                        with ui.list().classes('w-full').props('separator'):
                            for instance in machine_instances:
                                render_list_item(instance)
                    else:
                        with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch p-4'):
                            for instance in machine_instances:
                                render_card(instance)

    def change_view_to(mode: str):
        nonlocal view_mode
        view_mode = mode
        app.storage.user['instances_view_mode'] = mode
        cards_btn.props('color="primary"' if mode == 'cards' else 'color="grey"')
        list_btn.props('color="primary"' if mode == 'list' else 'color="grey"')
        render_instances.refresh()
    
    with ui.column().classes('w-full items-center min-h-screen py-10 px-4'):
        # Header
        with ui.row().classes('w-full max-w-5xl justify-between items-center mb-8'):
            with ui.row().classes('items-center gap-4'):
                back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round')
                ui.label('Instances').classes('text-4xl font-bold')
            
            with ui.row().classes('items-center gap-3'):
                with ui.button_group().props('outline rounded'):
                    cards_btn = ui.button(icon='grid_view', on_click=lambda: change_view_to('cards')).props(
                        'flat padding="xs sm"'
                    ).tooltip('Card view')
                    list_btn = ui.button(icon='format_list_bulleted', on_click=lambda: change_view_to('list')).props(
                        'flat padding="xs sm"'
                    ).tooltip('List view')
                    cards_btn.props('color="primary"' if view_mode == 'cards' else 'color="grey"')
                    list_btn.props('color="primary"' if view_mode == 'list' else 'color="grey"')
                theme_btn = ui.button(on_click=dark.toggle).props('flat round')
                theme_btn.bind_icon_from(dark, 'value', backward=lambda v: 'light_mode' if v else 'dark_mode')
                ui.button('Deploy New Platform', icon='add', on_click=lambda: ui.navigate.to('/deploy')).props('color="primary" rounded')
            
        if not instances:
            with ui.column().classes('w-full max-w-5xl items-center justify-center gap-4 py-20 border border-dashed rounded-2xl'):
                ui.icon('inbox', size='xl', color='gray')
                ui.label('No instances found').classes('text-lg text-grey-6')
                ui.button('Deploy your first platform', on_click=lambda: ui.navigate.to('/deploy')).props('outline color="primary" rounded')
        else:
            render_instances()
            ui.timer(0.1, refresh_all_statuses, once=True)
