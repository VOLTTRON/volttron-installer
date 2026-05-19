import httpx
from nicegui import ui
import asyncio

PROXY_URL = "http://127.0.0.1:8080/bacnet_api"

class BacnetScanState:
    def __init__(self):
        self.proxy_running = False
        self.local_ip = ""
        self.networks = []
        self.subnet_to_scan = ""
        self.discovered_devices = []
        self.is_scanning = False
        self.is_discovering = False

state = BacnetScanState()

async def get_host_ip():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PROXY_URL}/get_host_ip")
            if resp.status_code == 200:
                state.local_ip = resp.json().get("address", "")
                ui.notify(f"Auto-detected IP: {state.local_ip}", type='positive')
    except Exception as e:
        ui.notify(f"Error detecting IP: {e}", type='negative')

async def toggle_proxy():
    if state.proxy_running:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{PROXY_URL}/stop_proxy")
            state.proxy_running = False
            ui.notify("Proxy stopped", type='positive')
        except Exception as e:
            ui.notify(f"Error stopping proxy: {e}", type='negative')
    else:
        try:
            async with httpx.AsyncClient() as client:
                data = {"local_device_address": state.local_ip} if state.local_ip else {}
                resp = await client.post(f"{PROXY_URL}/start_proxy", data=data)
                result = resp.json()
                if result.get("status") == "done":
                    state.proxy_running = True
                    state.local_ip = result.get("address", state.local_ip)
                    ui.notify("Proxy started successfully", type='positive')
                else:
                    ui.notify(f"Failed to start: {result.get('error')}", type='negative')
        except Exception as e:
            ui.notify(f"Error starting proxy: {e}", type='negative')

async def discover_networks():
    state.is_discovering = True
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PROXY_URL}/discover_networks?verbose=false", timeout=30.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "done":
                    state.networks = data.get("networks", [])
                    ui.notify(f"Found {len(state.networks)} networks", type='positive')
                else:
                    ui.notify(f"Failed: {data.get('error')}", type='negative')
    except Exception as e:
        ui.notify(f"Error discovering networks: {e}", type='negative')
    finally:
        state.is_discovering = False

async def scan_subnet():
    if not state.subnet_to_scan:
        ui.notify("Please specify a subnet to scan", type='warning')
        return
        
    state.is_scanning = True
    state.discovered_devices = []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{PROXY_URL}/bacnet/scan_subnet", 
                data={"subnet": state.subnet_to_scan},
                timeout=300.0
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "done":
                    state.discovered_devices = data.get("devices", [])
                    ui.notify(f"Discovered {len(state.discovered_devices)} devices", type='positive')
                else:
                    ui.notify(f"Scan failed: {data.get('error')}", type='negative')
            else:
                ui.notify(f"Scan returned status {resp.status_code}", type='negative')
    except Exception as e:
        ui.notify(f"Error scanning: {e}", type='negative')
    finally:
        state.is_scanning = False

async def handle_toggle_proxy():
    await toggle_proxy()
    render.refresh()

async def handle_get_host_ip():
    await get_host_ip()
    render.refresh()

async def handle_discover_networks():
    render.refresh()
    await discover_networks()
    render.refresh()

async def handle_scan_subnet():
    render.refresh()
    await scan_subnet()
    render.refresh()

@ui.refreshable
def render():
    with ui.column().classes('w-full items-center py-10').style('min-height: 100vh;'):
        # Header
        with ui.row().classes('w-full max-w-6xl justify-between items-center mb-8'):
            with ui.row().classes('items-center gap-4'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round color="white"').style('transition: transform 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: translateX(-5px);')).on('mouseleave', lambda e: e.sender.style('transform: translateX(0);'))
                ui.label('BACnet Scan Tool').style('font-size: 2.5rem; font-weight: bold; color: #f3f4f6;')
                
            if state.proxy_running:
                ui.badge('Proxy Running', color='positive').classes('text-sm px-3 py-1')
            else:
                ui.badge('Proxy Offline', color='negative').classes('text-sm px-3 py-1')

        with ui.grid(columns='minmax(300px, 1fr) 2fr').classes('w-full max-w-6xl gap-6 items-start'):
            # Left Column (Controls)
            with ui.column().classes('w-full gap-6'):
                
                # Step 1: BACnet Proxy
                with ui.card().classes('w-full').style('background: rgba(30, 30, 36, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 1.5rem;'):
                    with ui.row().classes('items-center gap-2 mb-4 flex-nowrap'):
                        ui.icon('router', size='sm', color='#6366f1')
                        ui.label('Step 1: BACnet Proxy').style('font-weight: 600; font-size: 1.1rem; color: #e5e7eb;')
                    
                    ui.label('Start or stop the BACnet proxy service').style('color: #9ca3af; font-size: 0.85rem; margin-bottom: 1rem;')
                    
                    ui.input('Local Device Address (Optional)', value=state.local_ip).bind_value_to(state, 'local_ip').props('outlined dense bg-color="dark" color="primary"').classes('w-full mb-1')
                    ui.label('Leave blank to auto-detect').style('color: #6b7280; font-size: 0.75rem; margin-bottom: 1rem;')
                    
                    with ui.row().classes('w-full gap-2 flex-nowrap'):
                        ui.button('Start Proxy', on_click=handle_toggle_proxy).props('color="primary"').classes('flex-grow').bind_visibility_from(state, 'proxy_running', value=False)
                        ui.button('Stop Proxy', on_click=handle_toggle_proxy).props('color="negative" outline').classes('flex-grow').bind_visibility_from(state, 'proxy_running')
                        ui.button(icon='refresh', on_click=handle_get_host_ip).props('flat color="white"').tooltip('Auto-detect Host IP')

                # Step 2: Network Information
                with ui.card().classes('w-full').style('background: rgba(30, 30, 36, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 1.5rem;'):
                    with ui.row().classes('items-center gap-2 mb-4 flex-nowrap'):
                        ui.icon('network_check', size='sm', color='#a855f7')
                        ui.label('Step 2: Network Info (Optional)').style('font-weight: 600; font-size: 1.1rem; color: #e5e7eb;')
                    
                    ui.button('Discover Networks', on_click=handle_discover_networks).props('color="secondary" outline').classes('w-full mb-4')
                    
                    if state.is_discovering:
                        ui.spinner('dots', size='md', color='secondary').classes('self-center')
                    elif state.networks:
                        ui.label('Discovered Networks:').style('font-weight: bold; color: #d1d5db;')
                        with ui.column().classes('w-full gap-1'):
                            for net in state.networks:
                                ui.button(net, on_click=lambda n=net: setattr(state, 'subnet_to_scan', n) or render.refresh()).props('flat size="sm"').classes('w-full justify-start')
                                
                # Step 3: Scan for Devices
                with ui.card().classes('w-full').style('background: rgba(30, 30, 36, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 1.5rem;'):
                    with ui.row().classes('items-center gap-2 mb-4 flex-nowrap'):
                        ui.icon('search', size='sm', color='#ec4899')
                        ui.label('Step 3: Scan for Devices').style('font-weight: 600; font-size: 1.1rem; color: #e5e7eb;')
                    
                    ui.input('Subnet Range (CIDR)', value=state.subnet_to_scan).bind_value_to(state, 'subnet_to_scan').props('outlined dense bg-color="dark" color="primary"').classes('w-full mb-4')
                    
                    if state.is_scanning:
                        ui.button('Scanning...', icon='sync').props('color="accent" outline disable').classes('w-full')
                    else:
                        ui.button('Scan for Devices', on_click=handle_scan_subnet).props('color="accent"').classes('w-full').bind_enabled_from(state, 'proxy_running')
                        if not state.proxy_running:
                            ui.label('Proxy must be running to scan').style('color: #ef4444; font-size: 0.75rem; margin-top: 0.5rem; text-align: center; width: 100%;')

            # Right Column (Results)
            with ui.column().classes('w-full'):
                with ui.card().classes('w-full').style('background: rgba(30, 30, 36, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 1.5rem; min-height: 600px;'):
                    with ui.row().classes('items-center justify-between w-full mb-4'):
                        ui.label('Discovered Devices').style('font-size: 1.25rem; font-weight: 600; color: #e5e7eb;')
                        ui.badge(f"{len(state.discovered_devices)} Found", color='primary').classes('text-sm')
                    
                    if not state.discovered_devices:
                        with ui.column().classes('w-full h-full items-center justify-center gap-2').style('flex-grow: 1; opacity: 0.5;'):
                            ui.icon('device_hub', size='4rem', color='gray')
                            ui.label('No devices discovered yet').style('font-size: 1.1rem;')
                            ui.label('Start the proxy and run a scan to find devices.').style('font-size: 0.9rem;')
                    else:
                        columns = [
                            {'name': 'name', 'label': 'Device Name', 'field': 'object_name', 'sortable': True, 'align': 'left'},
                            {'name': 'id', 'label': 'Object ID', 'field': 'deviceIdentifier', 'sortable': True, 'align': 'left'},
                            {'name': 'ip', 'label': 'IP Address', 'field': 'address', 'sortable': True, 'align': 'left'},
                            {'name': 'vendor', 'label': 'Vendor ID', 'field': 'vendorID', 'sortable': True, 'align': 'center'}
                        ]
                        
                        rows = []
                        for dev in state.discovered_devices:
                            rows.append({
                                'object_name': dev.get('object_name', 'Unknown Device'),
                                'deviceIdentifier': dev.get('deviceIdentifier', ''),
                                'address': dev.get('address', ''),
                                'vendorID': dev.get('vendorID', '')
                            })
                            
                        ui.table(columns=columns, rows=rows, row_key='id').classes('w-full bg-[#1a1a20]').props('flat bordered dark')
