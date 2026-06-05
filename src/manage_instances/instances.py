from nicegui import ui, binding
import src.db as db
from src import theme

def render():
    dark_mode = theme.dark_mode()
    
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
                            ui.button(icon='more_vert').props('flat round color="gray"')
