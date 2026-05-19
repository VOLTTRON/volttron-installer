from nicegui import ui

def render():
    with ui.column().classes('w-full items-center justify-center').style('min-height: 80vh;'):
        ui.label('VOLTTRON Installer').style('font-size: 3rem; font-weight: bold; background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;')
        ui.label('Manage and deploy your VOLTTRON platforms with ease.').style('font-size: 1.2rem; color: #9ca3af; margin-bottom: 2rem;')
        
        with ui.row().classes('gap-4'):
            ui.button('Deploy New Platform', on_click=lambda: ui.navigate.to('/deploy')).props('color="primary" rounded size="lg"').style('background: linear-gradient(90deg, #6366f1, #a855f7); color: white; padding: 10px 30px; font-weight: bold; transition: transform 0.2s ease, box-shadow 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: scale(1.05); box-shadow: 0 0 15px rgba(168, 85, 247, 0.5);')).on('mouseleave', lambda e: e.sender.style('transform: scale(1); box-shadow: none;'))
            ui.button('View Instances', on_click=lambda: ui.navigate.to('/instances')).props('outline color="white" rounded size="lg"').style('padding: 10px 30px; font-weight: bold; transition: all 0.2s ease;').on('mouseenter', lambda e: e.sender.style('background: rgba(255,255,255,0.1);')).on('mouseleave', lambda e: e.sender.style('background: transparent;'))
            ui.button('BACnet Scan Tool', on_click=lambda: ui.navigate.to('/bacnet_scan')).props('outline color="secondary" rounded size="lg"').style('padding: 10px 30px; font-weight: bold; transition: all 0.2s ease;').on('mouseenter', lambda e: e.sender.style('background: rgba(168, 85, 247, 0.1);')).on('mouseleave', lambda e: e.sender.style('background: transparent;'))
