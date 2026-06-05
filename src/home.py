from nicegui import ui, binding
from src import theme

def render():
    dark_mode = theme.dark_mode()
    
    with ui.row().classes('absolute top-4 right-4 items-center gap-2'):
        theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
        theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
        binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')

    with ui.column().classes('w-full min-h-screen items-center justify-center gap-5 px-4'):
        ui.label('VOLTTRON Installer').classes('text-5xl font-bold text-primary text-center')
        ui.label('Manage and deploy your VOLTTRON platforms with ease.').classes('text-lg text-grey-6 text-center mb-4')
        
        with ui.row().classes('gap-4 justify-center'):
            ui.button('Deploy New Platform', on_click=lambda: ui.navigate.to('/deploy')).props('color="primary" rounded size="lg" icon="add"')
            
            instances_btn = ui.button('View Instances', on_click=lambda: ui.navigate.to('/instances')).props('outline rounded size="lg" icon="dns"')
            binding.bind_from(instances_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
            
            bacnet_btn = ui.button('BACnet Scan Tool', on_click=lambda: ui.navigate.to('/bacnet_scan')).props('outline rounded size="lg" icon="travel_explore"')
            binding.bind_from(bacnet_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'secondary' if val else 'secondary')
