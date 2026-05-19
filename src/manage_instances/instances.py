from nicegui import ui, binding
import src.db as db

def render():
    dark_mode = ui.dark_mode()
    
    with ui.column().classes('w-full items-center py-10').style('min-height: 100vh;'):
        # Header
        with ui.row().classes('w-full max-w-5xl justify-between items-center mb-8'):
            with ui.row().classes('items-center gap-4'):
                back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round').style('transition: transform 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: translateX(-5px);')).on('mouseleave', lambda e: e.sender.style('transform: translateX(0);'))
                binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                ui.label('Instances').style('font-size: 2.5rem; font-weight: bold; color: var(--text-color);')
            
            with ui.row().classes('items-center gap-3'):
                theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
                theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
                binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')
                ui.button('Deploy New Platform', icon='add', on_click=lambda: ui.navigate.to('/deploy')).props('color="primary" rounded').style('font-weight: bold; background: linear-gradient(90deg, #6366f1, #a855f7); color: white; transition: transform 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: scale(1.05);')).on('mouseleave', lambda e: e.sender.style('transform: scale(1);'))
            
        # Instances Grid
        instances = db.get_instances()
        
        if not instances:
            with ui.column().classes('w-full items-center justify-center gap-4 py-20 border border-dashed border-gray-700 rounded-2xl bg-[var(--sub-bg)]'):
                ui.icon('inbox', size='xl', color='gray')
                ui.label('No instances found').style('font-size: 1.2rem; color: var(--text-muted);')
                ui.button('Deploy your first platform', on_click=lambda: ui.navigate.to('/deploy')).props('outline color="primary" rounded')
        else:
            with ui.row().classes('w-full max-w-5xl gap-6'):
                for instance in instances:
                    with ui.card().classes('w-full max-w-sm').style('background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--card-border); border-radius: 16px; padding: 1.5rem; box-shadow: var(--card-shadow); transition: transform 0.3s ease, border-color 0.3s ease;').on('mouseenter', lambda e: e.sender.style('border-color: rgba(99, 102, 241, 0.5); transform: translateY(-5px);')).on('mouseleave', lambda e: e.sender.style('border-color: rgba(255, 255, 255, 0.1); transform: translateY(0);')):
                        with ui.row().classes('w-full justify-between items-start mb-4'):
                            with ui.column().classes('gap-1'):
                                ui.label(instance.get('name', 'Unknown')).style('font-size: 1.25rem; font-weight: 600; color: var(--text-color);')
                                ui.label(instance.get('type', 'Unknown Type')).style('font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; font-weight: 500;')
                        
                        ui.separator().classes('mb-4')
                        
                        with ui.column().classes('w-full gap-2 mb-6'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('dns', size='sm', color='gray')
                                ui.label(instance.get('host', 'localhost') if not instance.get('is_local') else 'localhost').style('color: var(--text-color);')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('link', size='sm', color='gray')
                                ui.label(instance.get('vip', 'N/A')).style('color: var(--text-color);')
                                
                        with ui.row().classes('w-full gap-2'):
                            ui.button('Manage', on_click=lambda instance_name=instance.get('name'): ui.navigate.to(f'/manage/{instance_name}')).props('color="primary" rounded flex-grow').style('font-weight: 600;')
                            ui.button(icon='more_vert').props('flat round color="gray"')
