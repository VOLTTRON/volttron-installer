import httpx
from nicegui import ui, binding
import asyncio
import re

_original_notify = ui.notify
def safe_notify(*args, **kwargs):
    try:
        _original_notify(*args, **kwargs)
    except Exception as e:
        print(f"Suppressed ui.notify error: {e}")
ui.notify = safe_notify

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
        
        # Object browser state
        self.selected_device = None
        self.objects = []
        self.objects_loading = False
        self.objects_page = 1
        self.objects_total_pages = 1

state = BacnetScanState()

# Dialog reference
object_dialog = None

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
    state.is_discovering = True
    try:
        await discover_networks()
    finally:
        state.is_discovering = False
        render_networks()

async def handle_scan_subnet():
    state.is_scanning = True
    try:
        await scan_subnet()
    finally:
        state.is_scanning = False
        render_devices()

networks_container = None
devices_container = None

def render_networks():
    networks_container.clear()
    with networks_container:
        if state.networks:
            ui.label('Discovered Networks:').style('font-weight: bold; color: var(--text-color);')
            with ui.column().classes('w-full gap-1'):
                for net in state.networks:
                    ui.button(net, on_click=lambda n=net: setattr(state, 'subnet_to_scan', n)).props('flat size="sm"').classes('w-full justify-start')

def render_devices():
    devices_container.clear()
    with devices_container:
        with ui.row().classes('items-center justify-between w-full mb-4'):
            ui.label('Discovered Devices').style('font-size: 1.25rem; font-weight: 600; color: var(--text-color);')
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
                {'name': 'vendor', 'label': 'Vendor ID', 'field': 'vendorID', 'sortable': True, 'align': 'center'},
                {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'}
            ]
            
            rows = []
            for dev in state.discovered_devices:
                rows.append({
                    'object_name': dev.get('object_name', 'Unknown Device'),
                    'deviceIdentifier': dev.get('deviceIdentifier', ''),
                    'address': dev.get('address', ''),
                    'vendorID': dev.get('vendorID', '')
                })
                
            dark_mode = ui.dark_mode()
            table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full bg-[var(--sub-bg)]').props('flat bordered')
            table.bind_prop('dark', dark_mode, 'value')
            
            table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn size="sm" color="accent" label="View Objects" @click="$parent.$emit('view_objects', props.row)" />
                </q-td>
            ''')
            table.on('view_objects', lambda e: asyncio.create_task(open_object_browser(e.args)))

# Object list pagination and reading
async def fetch_device_objects(device_address, device_id, page=1):
    state.objects_loading = True
    state.objects = []
    state.objects_page = page
    render_dialog_content.refresh()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{PROXY_URL}/bacnet/read_object_list_names",
                data={
                    "device_address": device_address,
                    "device_object_identifier": device_id,
                    "page": page,
                    "page_size": 25,
                    "force_fresh_read": "true"
                },
                timeout=120.0
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "done":
                    results = data.get("results", {}) or {}
                    pagination = data.get("pagination", {}) or {}
                    state.objects_total_pages = pagination.get("total_pages", 1)
                    
                    state.objects = []
                    for obj_id, props in results.items():
                        obj_type = "unknown"
                        obj_index = "0"
                        if ":" in obj_id:
                            obj_type, obj_index = obj_id.split(":", 1)
                        elif "," in obj_id:
                            obj_type, obj_index = obj_id.split(",", 1)
                            
                        state.objects.append({
                            "object_id": obj_id,
                            "object_type": obj_type,
                            "index": obj_index,
                            "name": props.get("object_name", "Unnamed Point"),
                            "present_value": props.get("present_value", "N/A"),
                            "units": props.get("units", "N/A"),
                            "description": props.get("description", "No description available")
                        })
                else:
                    ui.notify(f"Failed to fetch objects: {data.get('error')}", type='negative')
            else:
                ui.notify(f"Server returned status {resp.status_code}", type='negative')
    except Exception as e:
        ui.notify(f"Error fetching objects: {e}", type='negative')
    finally:
        state.objects_loading = False
        render_dialog_content.refresh()

def clean_point_name(name):
    # Replace spaces and hyphens with underscores
    cleaned = re.sub(r'[\s\-]+', '_', name)
    # Remove any non-alphanumeric/underscore characters
    cleaned = re.sub(r'[^\w]+', '', cleaned)
    return cleaned

def generate_and_download_csv(selected_rows, device_instance):
    if not selected_rows:
        ui.notify("Please select at least one point to generate driver", type='warning')
        return
        
    csv_lines = [
        "Reference Point Name,Volttron Point Name,Units,Units Details,BACnet Object Type,Property,Writable,Index,Write Priority,Description"
    ]
    
    for row in selected_rows:
        ref_name = clean_point_name(row['name'])
        vt_name = ref_name
        units = row['units'] or 'None'
        obj_type = row['object_type']
        obj_index = row['index']
        desc = row['description'] or 'No description'
        
        # Rule-based write capability
        writable = "TRUE" if "output" in obj_type.lower() or "value" in obj_type.lower() else "FALSE"
        
        line = f"{ref_name},{vt_name},{units},{units},{obj_type},presentValue,{writable},{obj_index},16,{desc}"
        csv_lines.append(line)
        
    csv_content = "\n".join(csv_lines)
    filename = f"volttron_driver_{device_instance}.csv"
    
    # Trigger client-side browser download
    ui.run_javascript(f'''
        var blob = new Blob([{repr(csv_content)}], {{type: 'text/csv;charset=utf-8;'}});
        var link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.setAttribute("download", "{filename}");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    ''')
    ui.notify(f"Generated {filename}", type='positive')

async def open_object_browser(row):
    state.selected_device = row
    state.objects = []
    state.objects_page = 1
    state.objects_total_pages = 1
    object_dialog.open()
    await fetch_device_objects(row['address'], row['deviceIdentifier'], page=1)

@ui.refreshable
def render_dialog_content():
    if not state.selected_device:
        return
        
    dev_name = state.selected_device.get('object_name', 'Unknown')
    dev_id = state.selected_device.get('deviceIdentifier', '')
    dev_addr = state.selected_device.get('address', '')
    
    dark_mode = ui.dark_mode()
    
    with ui.column().classes('w-full gap-4'):
        # Dialog Header
        with ui.row().classes('w-full justify-between items-center pb-4 border-b border-[var(--border-color)]'):
            with ui.column():
                ui.label(f"Browse Objects: {dev_name}").style('font-size: 1.5rem; font-weight: bold; color: var(--text-color);')
                ui.label(f"ID: {dev_id} | Address: {dev_addr}").style('font-size: 0.85rem; color: var(--text-muted);')
            
            close_icon_btn = ui.button(icon='close', on_click=object_dialog.close).props('flat round')
            binding.bind_from(close_icon_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
            
        if state.objects_loading:
            with ui.column().classes('w-full py-20 items-center justify-center gap-4'):
                ui.spinner('gears', size='4rem', color='accent')
                ui.label("Querying device registers over BACnet...").style('color: var(--text-muted); font-size: 1rem;')
        else:
            if not state.objects:
                with ui.column().classes('w-full py-10 items-center justify-center gap-2 opacity-50'):
                    ui.icon('layers_clear', size='4rem', color='gray')
                    ui.label('No objects found or queried').style('font-size: 1.1rem;')
            else:
                # Table of objects with native checkbox selection
                columns = [
                    {'name': 'type', 'label': 'Object Type', 'field': 'object_type', 'sortable': True, 'align': 'left'},
                    {'name': 'index', 'label': 'Index', 'field': 'index', 'sortable': True, 'align': 'left'},
                    {'name': 'name', 'label': 'Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                    {'name': 'value', 'label': 'Present Value', 'field': 'present_value', 'align': 'right'},
                    {'name': 'units', 'label': 'Units', 'field': 'units', 'align': 'left'},
                    {'name': 'description', 'label': 'Description', 'field': 'description', 'align': 'left'}
                ]
                
                table = ui.table(columns=columns, rows=state.objects, selection='multiple', row_key='object_id').classes('w-full bg-[var(--sub-bg)]').props('flat bordered')
                table.bind_prop('dark', dark_mode, 'value')
                
                # Bottom Actions Row
                with ui.row().classes('w-full justify-between items-center mt-4 flex-nowrap'):
                    # Pagination Controls
                    with ui.row().classes('items-center gap-2'):
                        prev_btn = ui.button(icon='chevron_left', on_click=lambda: fetch_device_objects(dev_addr, dev_id, state.objects_page - 1)).props('flat round').bind_enabled_from(state, 'objects_page', backward=lambda p: p > 1)
                        binding.bind_from(prev_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                        ui.label(f"Page {state.objects_page} of {state.objects_total_pages}").style('color: var(--text-muted);')
                        next_btn = ui.button(icon='chevron_right', on_click=lambda: fetch_device_objects(dev_addr, dev_id, state.objects_page + 1)).props('flat round').bind_enabled_from(state, 'objects_page', backward=lambda p: p < state.objects_total_pages)
                        binding.bind_from(next_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    
                    # CSV Generation Button
                    with ui.row().classes('gap-2'):
                        ui.button('Generate Driver Registry CSV', on_click=lambda: generate_and_download_csv(table.selected, dev_id)).props('color="accent" icon="download"').tooltip('Select points first using checkboxes')
                        close_btn = ui.button('Close', on_click=object_dialog.close).props('outline')
                        binding.bind_from(close_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')

@ui.refreshable
def render():
    global object_dialog, networks_container, devices_container
    
    dark_mode = ui.dark_mode()
    
    # BACnet Object Browser Dialog (Created once globally)
    with ui.dialog() as object_dialog:
        with ui.card().classes('w-full max-w-5xl p-6').style('background: var(--dialog-bg); border: 1px solid var(--border-color); border-radius: 16px;'):
            render_dialog_content()

    with ui.column().classes('w-full items-center py-10').style('min-height: 100vh;'):
        # Header
        with ui.row().classes('w-full max-w-6xl justify-between items-center mb-8'):
            with ui.row().classes('items-center gap-4'):
                back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round').style('transition: transform 0.2s ease;').on('mouseenter', lambda e: e.sender.style('transform: translateX(-5px);')).on('mouseleave', lambda e: e.sender.style('transform: translateX(0);'))
                binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                ui.label('BACnet Scan Tool').style('font-size: 2.5rem; font-weight: bold; color: var(--text-color);')
                
            with ui.row().classes('items-center gap-3'):
                if state.proxy_running:
                    ui.badge('Proxy Running', color='positive').classes('text-sm px-3 py-1')
                else:
                    ui.badge('Proxy Offline', color='negative').classes('text-sm px-3 py-1')
                theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
                theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
                binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')

        with ui.grid(columns='minmax(300px, 1fr) 2fr').classes('w-full max-w-6xl gap-6 items-start'):
            # Left Column (Controls)
            with ui.column().classes('w-full gap-6'):
                
                # Step 1: BACnet Proxy
                with ui.card().classes('w-full').style('background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--card-border); border-radius: 16px; padding: 1.5rem;'):
                    with ui.row().classes('items-center gap-2 mb-4 flex-nowrap'):
                        ui.icon('router', size='sm', color='#6366f1')
                        ui.label('Step 1: BACnet Proxy').style('font-weight: 600; font-size: 1.1rem; color: var(--text-color);')
                    
                    ui.label('Start or stop the BACnet proxy service').style('color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem;')
                    
                    ui.input('Local Device Address (Optional)', value=state.local_ip).bind_value_to(state, 'local_ip').props('outlined dense color="primary"').classes('w-full mb-1')
                    ui.label('Leave blank to auto-detect').style('color: var(--text-muted); font-size: 0.75rem; margin-bottom: 1rem;')
                    
                    with ui.row().classes('w-full gap-2 flex-nowrap'):
                        ui.button('Start Proxy', on_click=handle_toggle_proxy).props('color="primary"').classes('flex-grow').bind_visibility_from(state, 'proxy_running', value=False)
                        ui.button('Stop Proxy', on_click=handle_toggle_proxy).props('color="negative" outline').classes('flex-grow').bind_visibility_from(state, 'proxy_running')
                        detect_btn = ui.button(icon='refresh', on_click=handle_get_host_ip).props('flat').tooltip('Auto-detect Host IP')
                        binding.bind_from(detect_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')

                # Step 2: Network Information
                with ui.card().classes('w-full').style('background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--card-border); border-radius: 16px; padding: 1.5rem;'):
                    with ui.row().classes('items-center gap-2 mb-4 flex-nowrap'):
                        ui.icon('network_check', size='sm', color='#a855f7')
                        ui.label('Step 2: Network Info (Optional)').style('font-weight: 600; font-size: 1.1rem; color: var(--text-color);')
                    
                    ui.button('Discover Networks', on_click=handle_discover_networks).props('color="secondary" outline').classes('w-full mb-4').bind_visibility_from(state, 'is_discovering', backward=lambda d: not d)
                    ui.button('Discovering...', icon='sync').props('color="secondary" outline disable').classes('w-full mb-4').bind_visibility_from(state, 'is_discovering')
                    networks_container = ui.column().classes('w-full')
                    render_networks()
                                
                # Step 3: Scan for Devices
                with ui.card().classes('w-full').style('background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--card-border); border-radius: 16px; padding: 1.5rem;'):
                    with ui.row().classes('items-center gap-2 mb-4 flex-nowrap'):
                        ui.icon('search', size='sm', color='#ec4899')
                        ui.label('Step 3: Scan for Devices').style('font-weight: 600; font-size: 1.1rem; color: var(--text-color);')
                    
                    ui.input('Subnet Range (CIDR)', value=state.subnet_to_scan).bind_value_to(state, 'subnet_to_scan').props('outlined dense color="primary"').classes('w-full mb-4')
                    ui.button('Scanning...', icon='sync').props('color="accent" outline disable').classes('w-full').bind_visibility_from(state, 'is_scanning')
                    ui.button('Scan for Devices', on_click=handle_scan_subnet).props('color="accent"').classes('w-full').bind_enabled_from(state, 'proxy_running').bind_visibility_from(state, 'is_scanning', backward=lambda s: not s)
                    ui.label('Proxy must be running to scan').style('color: #ef4444; font-size: 0.75rem; margin-top: 0.5rem; text-align: center; width: 100%;').bind_visibility_from(state, 'proxy_running', backward=lambda p: not p)

            # Right Column (Results)
            with ui.column().classes('w-full'):
                with ui.card().classes('w-full').style('background: var(--card-bg); backdrop-filter: blur(10px); border: 1px solid var(--card-border); border-radius: 16px; padding: 1.5rem; min-height: 600px;'):
                    devices_container = ui.column().classes('w-full h-full')
                    render_devices()
