from nicegui import ui, binding

def render():
    dark_mode = ui.dark_mode()
    
    with ui.row().classes('absolute top-4 right-4 items-center gap-2'):
        theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
        theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
        binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')

    with ui.column().classes('w-full items-center justify-center').style('min-height: 80vh;'):
        ui.image('/assets/logo-mini.png').style('width: 96px; height: auto; margin-bottom: 1.25rem;')
        ui.label('VOLTTRON Installer').style('font-size: 3rem; font-weight: bold; background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;')
        ui.label('Manage and deploy your VOLTTRON platforms with ease.').style('font-size: 1.2rem; color: var(--text-muted); margin-bottom: 2rem;')
        
        with ui.row().classes('gap-4'):
            ui.button('Deploy New Platform', on_click=lambda: ui.navigate.to('/deploy')).props('color="primary" rounded size="lg"').style('background: linear-gradient(90deg, #6366f1, #a855f7); color: white; padding: 10px 30px; font-weight: bold; transition: transform 0.2s ease, box-shadow 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: scale(1.05); box-shadow: 0 0 15px rgba(168, 85, 247, 0.5);')).on('mouseleave', lambda e: e.sender.style('transform: scale(1); box-shadow: none;'))
            
            # View Instances button outline color adaptation
            instances_btn = ui.button('View Instances', on_click=lambda: ui.navigate.to('/instances')).props('outline rounded size="lg"').style('padding: 10px 30px; font-weight: bold; transition: all 0.2s ease;')
            binding.bind_from(instances_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
            instances_btn.on('mouseenter', lambda e: e.sender.style('background: var(--card-border);')).on('mouseleave', lambda e: e.sender.style('background: transparent;'))
            
            # BACnet Scan Tool button outline color adaptation
            bacnet_btn = ui.button('BACnet Scan Tool', on_click=lambda: ui.navigate.to('/bacnet_scan')).props('outline rounded size="lg"').style('padding: 10px 30px; font-weight: bold; transition: all 0.2s ease;')
            binding.bind_from(bacnet_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'secondary' if val else 'secondary')
            bacnet_btn.on('mouseleave', lambda e: e.sender.style('background: transparent;'))

