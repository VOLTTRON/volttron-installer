import httpx
from nicegui import ui
from src.dark import dark_mode_control
import asyncio
import csv
import io
import json
import re
import zipfile

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
        self.scan_task = None
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
                resp = await client.post(f"{PROXY_URL}/stop_proxy", timeout=15.0)
                resp.raise_for_status()
                result = resp.json()
            if result.get("status") == "done":
                state.proxy_running = False
                ui.notify(result.get("message", "Proxy stopped"), type='positive')
            else:
                ui.notify(f"Failed to stop proxy: {result.get('error', 'unknown error')}", type='negative')
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
    except asyncio.CancelledError:
        ui.notify("Scan canceled", type='warning')
    except Exception as e:
        ui.notify(f"Error scanning: {e}", type='negative')
    finally:
        state.is_scanning = False
        state.scan_task = None

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
    if state.is_scanning:
        return
    state.is_scanning = True
    state.scan_task = asyncio.current_task()
    try:
        await scan_subnet()
    finally:
        state.is_scanning = False
        state.scan_task = None
        render_devices()

def cancel_scan():
    if state.scan_task and not state.scan_task.done():
        state.scan_task.cancel()
        ui.notify("Canceling scan...", type='warning')

networks_container = None
devices_container = None

def render_networks():
    networks_container.clear()
    with networks_container:
        if state.networks:
            ui.label('Discovered Networks:').classes('font-bold')
            with ui.column().classes('w-full gap-1'):
                for net in state.networks:
                    ui.button(net, on_click=lambda n=net: setattr(state, 'subnet_to_scan', n)).props('flat size="sm"').classes('w-full justify-start')

def render_devices():
    devices_container.clear()
    with devices_container:
        with ui.row().classes('items-center justify-between w-full mb-4'):
            ui.label('Discovered Devices').classes('text-xl font-semibold')
            ui.badge(f"{len(state.discovered_devices)} Found", color='primary').classes('text-sm')
        
        if not state.discovered_devices:
            with ui.column().classes('w-full h-full flex-grow items-center justify-center gap-2 opacity-50'):
                ui.icon('device_hub', size='4rem', color='gray')
                ui.label('No devices discovered yet').classes('text-lg')
                ui.label('Start the proxy and run a scan to find devices.').classes('text-grey-6 text-sm')
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
                dev_id = dev.get('deviceIdentifier', '')
                rows.append({
                    'object_name': dev.get('object_name') or dev_id or 'Unknown Device',
                    'deviceIdentifier': dev_id,
                    'address': dev.get('address', ''),
                    'vendorID': dev.get('vendorID', '')
                })
                
            table = ui.table(columns=columns, rows=rows, row_key='deviceIdentifier').classes('w-full').props('flat bordered')

            
            table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn size="sm" color="accent" label="View Objects" @click="$parent.$emit('view_objects', props.row)" />
                    <q-btn size="sm" color="primary" label="Config" class="q-ml-sm" @click="$parent.$emit('download_config', props.row)" />
                </q-td>
            ''')
            table.on('view_objects', open_object_browser)
            table.on('download_config', generate_and_download_config_bundle)

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

def safe_config_name(name):
    cleaned = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(name or '').strip())
    cleaned = cleaned.strip('._-')
    return cleaned or 'bacnet_device'

def bacnet_object_type_for_config(object_type):
    parts = re.split(r'[-_\s]+', str(object_type or '').strip())
    if not parts:
        return 'unknown'
    return parts[0] + ''.join(part[:1].upper() + part[1:] for part in parts[1:])

def device_instance_from_identifier(identifier):
    text = str(identifier or '')
    if ',' in text:
        text = text.split(',', 1)[1]
    match = re.search(r'\d+', text)
    return int(match.group(0)) if match else 0

def writable_for_object_type(object_type):
    lowered = str(object_type or '').lower()
    return 'TRUE' if lowered.endswith('output') or lowered.endswith('value') else 'FALSE'

SUPPORTED_BACNET_REGISTRY_OBJECT_TYPES = {
    'analogInput',
    'analogOutput',
    'analogValue',
    'binaryInput',
    'binaryOutput',
    'binaryValue',
    'multiStateInput',
    'multiStateOutput',
    'multiStateValue',
}

def is_supported_bacnet_registry_object(object_type):
    return bacnet_object_type_for_config(object_type) in SUPPORTED_BACNET_REGISTRY_OBJECT_TYPES

def registry_csv_content(objects):
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow([
        'Point Name',
        'Volttron Point Name',
        'Units',
        'Unit Details',
        'BACnet Object Type',
        'Property',
        'Writable',
        'Index',
        'Notes',
    ])

    for row in objects:
        if not is_supported_bacnet_registry_object(row.get('object_type')):
            continue

        point_name = row.get('name') or f"{row.get('object_type', 'object')}_{row.get('index', '')}"
        units = '' if row.get('units') in {None, 'N/A'} else str(row.get('units'))
        writer.writerow([
            point_name,
            point_name,
            units,
            '',
            bacnet_object_type_for_config(row.get('object_type')),
            'presentValue',
            writable_for_object_type(row.get('object_type')),
            row.get('index', ''),
            row.get('description') or '',
        ])

    return output.getvalue()

def device_config_content(device, registry_filename):
    return json.dumps({
        'driver_config': {
            'device_address': device.get('address', ''),
            'device_id': device_instance_from_identifier(device.get('deviceIdentifier')),
        },
        'driver_type': 'bacnet',
        'registry_config': f'config://{registry_filename}',
        'interval': 60,
        'timezone': 'UTC',
    }, indent=4)

async def fetch_all_device_objects(device_address, device_id):
    all_objects = []
    page = 1
    total_pages = 1

    async with httpx.AsyncClient() as client:
        while page <= total_pages:
            resp = await client.post(
                f"{PROXY_URL}/bacnet/read_object_list_names",
                data={
                    "device_address": device_address,
                    "device_object_identifier": device_id,
                    "page": page,
                    "page_size": 100,
                    "force_fresh_read": "true" if page == 1 else "false",
                },
                timeout=180.0
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Server returned status {resp.status_code}")

            data = resp.json()
            if data.get("status") != "done":
                raise RuntimeError(data.get("error") or "Failed to fetch BACnet objects")

            results = data.get("results", {}) or {}
            pagination = data.get("pagination", {}) or {}
            total_pages = int(pagination.get("total_pages") or total_pages)

            for obj_id, props in results.items():
                obj_type = "unknown"
                obj_index = "0"
                if ":" in obj_id:
                    obj_type, obj_index = obj_id.split(":", 1)
                elif "," in obj_id:
                    obj_type, obj_index = obj_id.split(",", 1)

                all_objects.append({
                    "object_id": obj_id,
                    "object_type": obj_type,
                    "index": obj_index,
                    "name": props.get("object_name", "Unnamed Point"),
                    "present_value": props.get("present_value", "N/A"),
                    "units": props.get("units", "N/A"),
                    "description": props.get("description", ""),
                })

            page += 1

    return all_objects

def build_config_bundle(device, objects):
    device_id = device_instance_from_identifier(device.get('deviceIdentifier'))
    dev_name = device.get('object_name')
    if dev_name:
        base_name = safe_config_name(f"{dev_name}_{device_id}")
    else:
        base_name = safe_config_name(device.get('deviceIdentifier') or str(device_id))
    registry_filename = f"{base_name}.csv"
    config_filename = f"{base_name}.config"
    readme_filename = f"{base_name}_README.txt"

    csv_content = registry_csv_content(objects)
    config_content = device_config_content(device, registry_filename)
    readme_content = (
        "Generated BACnet Platform Driver config bundle.\n\n"
        "Store these files with:\n"
        f"vctl config store platform.driver {registry_filename} {registry_filename} --csv\n"
        f"vctl config store platform.driver devices/{base_name} {config_filename}\n"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(config_filename, config_content)
        zip_file.writestr(registry_filename, csv_content)
        zip_file.writestr(readme_filename, readme_content)

    return f"{base_name}_bacnet_driver_config.zip", buffer.getvalue()

def download_config_bundle(device, objects):
    zip_filename, zip_content = build_config_bundle(device, objects)
    ui.download(zip_content, filename=zip_filename, media_type='application/zip')

async def generate_and_download_config_bundle(device):
    if hasattr(device, 'args'):
        device = device.args
    try:
        ui.notify("Reading all BACnet objects for config bundle...", type='info')
        objects = await fetch_all_device_objects(device.get('address'), device.get('deviceIdentifier'))
        if not objects:
            ui.notify("No objects found for this device", type='warning')
            return
        download_config_bundle(device, objects)
    except Exception as e:
        ui.notify(f"Failed to generate config bundle: {e}", type='negative')

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
    if hasattr(row, 'args'):
        row = row.args
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
        
    dev_id = state.selected_device.get('deviceIdentifier', '')
    dev_name = state.selected_device.get('object_name') or dev_id or 'Unknown'
    dev_addr = state.selected_device.get('address', '')

    with ui.column().classes('w-full gap-4'):
        # Dialog Header
        with ui.row().classes('w-full justify-between items-center pb-4 border-b'):
            with ui.column():
                ui.label(f"Browse Objects: {dev_name}").classes('text-2xl font-bold')
                ui.label(f"ID: {dev_id} | Address: {dev_addr}").classes('text-grey-6 text-sm')
            
            close_icon_btn = ui.button(icon='close', on_click=object_dialog.close).props('flat round')

            
        if state.objects_loading:
            with ui.column().classes('w-full py-20 items-center justify-center gap-4'):
                ui.spinner('gears', size='4rem', color='accent')
                ui.label("Querying device registers over BACnet...").classes('text-grey-6')
        else:
            if not state.objects:
                with ui.column().classes('w-full py-10 items-center justify-center gap-2 opacity-50'):
                    ui.icon('layers_clear', size='4rem', color='gray')
                    ui.label('No objects found or queried').classes('text-lg')
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
                
                table = ui.table(columns=columns, rows=state.objects, selection='multiple', row_key='object_id').classes('w-full').props('flat bordered')

                
                # Bottom Actions Row
                with ui.row().classes('w-full justify-between items-center mt-4 flex-nowrap'):
                    # Pagination Controls
                    with ui.row().classes('items-center gap-2'):
                        prev_btn = ui.button(icon='chevron_left', on_click=lambda: fetch_device_objects(dev_addr, dev_id, state.objects_page - 1)).props('flat round').bind_enabled_from(state, 'objects_page', backward=lambda p: p > 1)

                        ui.label(f"Page {state.objects_page} of {state.objects_total_pages}").classes('text-grey-6')
                        next_btn = ui.button(icon='chevron_right', on_click=lambda: fetch_device_objects(dev_addr, dev_id, state.objects_page + 1)).props('flat round').bind_enabled_from(state, 'objects_page', backward=lambda p: p < state.objects_total_pages)

                    
                    # CSV Generation Button
                    with ui.row().classes('gap-2'):
                        ui.button('Download Driver Config Bundle', on_click=lambda: generate_and_download_config_bundle(state.selected_device)).props('color="primary" icon="archive"').tooltip('Downloads device config and registry CSV for all discovered objects')
                        ui.button('Generate Driver Registry CSV', on_click=lambda: generate_and_download_csv(table.selected, dev_id)).props('color="accent" icon="download"').tooltip('Select points first using checkboxes')
                        close_btn = ui.button('Close', on_click=object_dialog.close).props('outline')

@ui.refreshable
def render():
    global object_dialog, networks_container, devices_container
    
    dark = dark_mode_control()
    
    # BACnet Object Browser Dialog (Created once globally)
    with ui.dialog() as object_dialog:
        with ui.card().classes('w-full p-6 max-w-5xl'):
            render_dialog_content()

    with ui.column().classes('w-full items-center min-h-screen py-10 px-4'):
        # Header
        with ui.row().classes('w-full max-w-6xl justify-between items-center mb-8'):
            with ui.row().classes('items-center gap-4'):
                back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat round')

                ui.label('BACnet Scan Tool').classes('text-4xl font-bold')
                
            with ui.row().classes('items-center gap-3'):
                if state.proxy_running:
                    ui.badge('Proxy Running', color='positive').classes('text-sm px-3 py-1')
                else:
                    ui.badge('Proxy Offline', color='negative').classes('text-sm px-3 py-1')
                theme_btn = ui.button(on_click=dark.toggle).props('flat round')
                theme_btn.bind_icon_from(dark, 'value', backward=lambda v: 'light_mode' if v else 'dark_mode')

        with ui.grid(columns='minmax(300px, 1fr) 2fr').classes('w-full max-w-6xl gap-6 items-start'):
            # Left Column (Controls)
            with ui.column().classes('w-full gap-6'):
                
                # Step 1: BACnet Proxy
                with ui.card().classes('w-full p-6'):
                    with ui.row().classes('items-center gap-2 mb-4 flex-nowrap'):
                        ui.icon('router', size='sm', color='primary')
                        ui.label('Step 1: BACnet Proxy').classes('text-lg font-semibold')
                    
                    ui.label('Start or stop the BACnet proxy service').classes('text-grey-6 text-sm mb-4')
                    
                    ui.input('Local Device Address (Optional)', value=state.local_ip).bind_value_to(state, 'local_ip').props('outlined dense color="primary"').classes('w-full mb-1')
                    ui.label('Leave blank to auto-detect').classes('text-grey-6 text-sm mb-4')
                    
                    with ui.row().classes('w-full gap-2 flex-nowrap'):
                        ui.button('Start Proxy', on_click=handle_toggle_proxy).props('color="primary"').classes('flex-grow').bind_visibility_from(state, 'proxy_running', value=False)
                        ui.button('Stop Proxy', on_click=handle_toggle_proxy).props('color="negative" outline').classes('flex-grow').bind_visibility_from(state, 'proxy_running')
                        detect_btn = ui.button(icon='refresh', on_click=handle_get_host_ip).props('flat').tooltip('Auto-detect Host IP')

                # Step 2: Network Information
                with ui.card().classes('w-full p-6'):
                    with ui.row().classes('items-center gap-2 mb-4 flex-nowrap'):
                        ui.icon('network_check', size='sm', color='secondary')
                        ui.label('Step 2: Network Info (Optional)').classes('text-lg font-semibold')
                    
                    ui.button('Discover Networks', on_click=handle_discover_networks).props('color="secondary" outline').classes('w-full mb-4').bind_visibility_from(state, 'is_discovering', backward=lambda d: not d)
                    ui.button('Discovering...', icon='sync').props('color="secondary" outline disable').classes('w-full mb-4').bind_visibility_from(state, 'is_discovering')
                    networks_container = ui.column().classes('w-full')
                    render_networks()
                                
                # Step 3: Scan for Devices
                with ui.card().classes('w-full p-6'):
                    with ui.row().classes('items-center gap-2 mb-4 flex-nowrap'):
                        ui.icon('search', size='sm', color='accent')
                        ui.label('Step 3: Scan for Devices').classes('text-lg font-semibold')
                    
                    ui.input('Subnet Range (CIDR)', value=state.subnet_to_scan).bind_value_to(state, 'subnet_to_scan').props('outlined dense color="primary"').classes('w-full mb-4')
                    with ui.column().classes('w-full gap-2').bind_visibility_from(state, 'is_scanning'):
                        with ui.row().classes('items-center justify-center gap-2 w-full'):
                            ui.spinner('dots', size='lg', color='accent')
                            ui.label('Scanning...').classes('text-grey-6 text-sm')
                        ui.button('Cancel Scan', icon='close', on_click=cancel_scan).props('color="negative" outline').classes('w-full')
                    ui.button('Scan for Devices', on_click=handle_scan_subnet).props('color="accent"').classes('w-full').bind_enabled_from(state, 'proxy_running').bind_visibility_from(state, 'is_scanning', backward=lambda s: not s)
                    ui.label('Proxy must be running to scan').classes('text-negative text-xs mt-2 text-center w-full').bind_visibility_from(state, 'proxy_running', backward=lambda p: not p)

            # Right Column (Results)
            with ui.column().classes('w-full'):
                with ui.card().classes('w-full p-6 min-h-96'):
                    devices_container = ui.column().classes('w-full h-full')
                    render_devices()
