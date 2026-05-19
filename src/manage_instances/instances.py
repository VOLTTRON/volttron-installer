from nicegui import ui
import src.db as db

def render():
    with ui.column().classes('w-full items-center py-10').style('min-height: 100vh;'):
        # Header
        with ui.row().classes('w-full max-w-5xl justify-between items-center mb-8'):
            with ui.row().classes('items-center gap-4'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round color="white"').style('transition: transform 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: translateX(-5px);')).on('mouseleave', lambda e: e.sender.style('transform: translateX(0);'))
                ui.label('Instances').style('font-size: 2.5rem; font-weight: bold; color: #f3f4f6;')
            
            ui.button('Deploy New Platform', icon='add', on_click=lambda: ui.navigate.to('/deploy')).props('color="primary" rounded').style('font-weight: bold; background: linear-gradient(90deg, #6366f1, #a855f7); color: white; transition: transform 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: scale(1.05);')).on('mouseleave', lambda e: e.sender.style('transform: scale(1);'))
            
        # Instances Grid
        instances = db.get_instances()
        
        if not instances:
            with ui.column().classes('w-full items-center justify-center gap-4 py-20 border border-dashed border-gray-700 rounded-2xl bg-[#1a1a20]'):
                ui.icon('inbox', size='xl', color='gray')
                ui.label('No instances found').style('font-size: 1.2rem; color: #9ca3af;')
                ui.button('Deploy your first platform', on_click=lambda: ui.navigate.to('/deploy')).props('outline color="primary" rounded')
        else:
            with ui.row().classes('w-full max-w-5xl gap-6'):
                for instance in instances:
                    with ui.card().classes('w-full max-w-sm').style('background: rgba(30, 30, 36, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 1.5rem; box-shadow: 0 10px 30px rgba(0,0,0,0.5); transition: transform 0.3s ease, border-color 0.3s ease;').on('mouseenter', lambda e: e.sender.style('border-color: rgba(99, 102, 241, 0.5); transform: translateY(-5px);')).on('mouseleave', lambda e: e.sender.style('border-color: rgba(255, 255, 255, 0.1); transform: translateY(0);')):
                        with ui.row().classes('w-full justify-between items-start mb-4'):
                            with ui.column().classes('gap-1'):
                                ui.label(instance.get('name', 'Unknown')).style('font-size: 1.25rem; font-weight: 600; color: #e5e7eb;')
                                ui.label(instance.get('type', 'Unknown Type')).style('font-size: 0.8rem; color: #9ca3af; text-transform: uppercase; font-weight: 500;')
                        
                        ui.separator().classes('mb-4')
                        
                        with ui.column().classes('w-full gap-2 mb-6'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('dns', size='sm', color='gray')
                                ui.label(instance.get('host', 'localhost') if not instance.get('is_local') else 'localhost').style('color: #d1d5db;')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('link', size='sm', color='gray')
                                ui.label(instance.get('vip', 'N/A')).style('color: #d1d5db;')
                                
                        with ui.row().classes('w-full gap-2'):
                            ui.button('Manage', on_click=lambda instance_name=instance.get('name'): ui.navigate.to(f'/manage/{instance_name}')).props('color="primary" rounded flex-grow').style('font-weight: 600;')
                            ui.button(icon='more_vert').props('flat round color="gray"')
