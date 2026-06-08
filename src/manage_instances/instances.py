from nicegui import ui, binding
import src.db as db
from src import theme
from src.manage_instances import agent_management
from src.manage_instances.start_platform import start_platform_command

def render():
    dark_mode = theme.dark_mode()

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
        except Exception as error:
            progress_dialog.close()
            ui.notify(f'{action_name} failed: {error}', type='negative')

    def request_sudo(instance: dict, action_name: str, action, button_icon: str, button_color: str):
        with ui.dialog() as sudo_dialog, ui.card().classes('p-6 gap-4 w-full max-w-lg'):
            ui.label(f'{action_name} {instance.get("name", "instance")}').classes('text-lg font-bold')
            ui.label('Local systemd access requires sudo. The password is used once and is not saved.').classes(theme.muted())
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
                ui.label('This removes the systemd service, virtual environment, VOLTTRON_HOME, and installer record.').classes(theme.muted())
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
                ui.menu_item('Start', on_click=handle_start)
                ui.menu_item('Stop', on_click=handle_stop)
                ui.separator()
                ui.menu_item('Delete', on_click=handle_delete)
    
    with ui.column().classes(theme.page_container('py-10 px-4')):
        # Header
        with ui.row().classes('w-full max-w-5xl justify-between items-center mb-8'):
            with ui.row().classes('items-center gap-4'):
                back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round')
                binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                ui.label('Instances').classes(theme.title())
            
            with ui.row().classes('items-center gap-3'):
                theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
                theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
                binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')
                ui.button('Deploy New Platform', icon='add', on_click=lambda: ui.navigate.to('/deploy')).props('color="primary" rounded')
            
        # Instances Grid
        instances = db.get_instances()
        
        if not instances:
            with ui.column().classes('w-full max-w-5xl items-center justify-center gap-4 py-20 border border-dashed rounded-2xl'):
                ui.icon('inbox', size='xl', color='gray')
                ui.label('No instances found').classes('text-lg text-grey-6')
                ui.button('Deploy your first platform', on_click=lambda: ui.navigate.to('/deploy')).props('outline color="primary" rounded')
        else:
            with ui.row().classes('w-full max-w-5xl gap-6'):
                for instance in instances:
                    with ui.card().classes(theme.card('max-w-sm')):
                        with ui.row().classes('w-full justify-between items-start mb-4'):
                            with ui.column().classes('gap-1'):
                                ui.label(instance.get('name', 'Unknown')).classes(theme.section_title())
                                ui.label(instance.get('type', 'Unknown Type')).classes('text-xs text-grey-6 uppercase font-medium')
                        
                        ui.separator().classes('mb-4')
                        
                        with ui.column().classes('w-full gap-2 mb-6'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('dns', size='sm', color='gray')
                                ui.label(instance.get('host', 'localhost') if not instance.get('is_local') else 'localhost')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('link', size='sm', color='gray')
                                ui.label(instance.get('vip', 'N/A'))
                                
                        with ui.row().classes('w-full gap-2'):
                            ui.button('Manage', on_click=lambda instance_name=instance.get('name'): ui.navigate.to(f'/manage/{instance_name}')).props('color="primary" rounded flex-grow')
                            render_instance_menu(instance)
