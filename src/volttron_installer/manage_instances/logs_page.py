"""Pure Python/NiceGUI log viewer page.

Simpler, extremely robust, and fully integrated into the NiceGUI framework.
Maintains a live-only scrollable view of the active volttron.log.
Users can select historical/rotated files purely to stream-download them on-demand
with a visual progress bar reflecting byte transfer progress.
No client-side virtual scrolling, zero flashing, and zero JS scroll state bugs.
"""
from urllib.parse import quote, unquote
import html

from nicegui import ui

import volttron_installer.db as db
from volttron_installer.dark import dark_mode_control
from volttron_installer.manage_instances import agent_management

DEFAULT_LINES = 1000
POLL_INTERVAL_SEC = 4.0
CHUNK_BYTES = 131072  # 128 KB chunks (~1000-1500 lines)


def _get_level_class(line: str) -> str:
    """Return Tailwind color classes based on log level."""
    upper = line.upper()
    if 'ERROR' in upper or 'CRITICAL' in upper:
        return 'text-red-400 font-semibold'
    if 'WARNING' in upper or 'WARN' in upper:
        return 'text-amber-400'
    if 'DEBUG' in upper:
        return 'text-sky-400'
    if 'INFO' in upper:
        return 'text-emerald-400'
    return 'text-slate-300'


def _get_bytes_size(lines_list: list[str]) -> int:
    """Calculate approximate UTF-8 bytes for a list of lines including newlines."""
    return sum(len(line.encode('utf-8', errors='replace')) + 1 for line in lines_list)


def render(instance_name: str) -> None:
    dark_mode_control()
    instance = next(
        (item for item in db.get_instances() if item.get('name') == instance_name), None
    )
    if not instance:
        with ui.column().classes('w-full items-center py-20'):
            ui.label(f'Instance "{instance_name}" not found').classes(
                'text-red-500 text-2xl font-bold mb-4'
            )
            ui.button(
                'Back to Instances',
                icon='arrow_back',
                on_click=lambda: ui.navigate.to('/instances'),
            ).props('outline')
        return

    # Check if platform web API coordinates are present
    web_address = instance.get("web_bind_address", "")
    if not web_address:
        with ui.column().classes('w-full items-center py-20 px-4'):
            ui.icon('warning', size='lg').classes('text-amber-500 mb-4')
            ui.label('Platform Web API required for log viewing.').classes('text-lg font-semibold text-center')
            ui.label('Please configure Web Bind Address and Admin credentials on this instance.').classes('text-grey-6 text-sm text-center mb-6')
            ui.button(
                'Back to Manage',
                icon='arrow_back',
                on_click=lambda: ui.navigate.to(f'/manage/{quote(instance_name, safe="")}'),
            ).props('outline')
        return

    # Inject CSS for beautiful custom dark scrollbars matching our slate-955 terminal theme
    ui.add_head_html("""
    <style>
      /* Style scrollbars for all scroll containers */
      ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
      }
      ::-webkit-scrollbar-track {
        background: #020617; /* Slate 950 */
      }
      ::-webkit-scrollbar-thumb {
        background: #1e293b; /* Slate 800 */
        border-radius: 5px;
        border: 2px solid #020617;
      }
      ::-webkit-scrollbar-thumb:hover {
        background: #334155; /* Slate 700 */
      }
      /* Firefox scrollbar styling */
      * {
        scrollbar-width: thin;
        scrollbar-color: #1e293b #020617;
      }
    </style>
    """)

    # Reset the default NiceGUI page container to be 100% full-width, full-height and zero padding
    ui.query('.nicegui-content').classes('p-0 gap-0 w-full max-w-none h-screen overflow-hidden')

    # Full viewport container with absolute layout
    with ui.column().classes('w-full h-full gap-0 p-0 m-0 overflow-hidden relative bg-slate-950'):
        
        # Floating Header & Back Button Overlay (top-left)
        with ui.row().classes('fixed top-4 left-4 z-50 items-center gap-2 bg-slate-900/85 dark:bg-zinc-900/85 backdrop-blur-md px-3 py-1.5 rounded-full border border-slate-800 dark:border-zinc-800 shadow-lg'):
            ui.button(
                icon='arrow_back',
                on_click=lambda: ui.navigate.to(f'/manage/{quote(instance_name, safe="")}'),
            ).props('flat round dense color="white"').classes('text-white')
            ui.label('Logs').classes('text-white text-xs font-bold font-mono tracking-wider uppercase select-none')
            status_badge = ui.badge('Connecting...', color='orange').props('outline dense')
            file_size_label = ui.label('').classes('text-[10px] text-slate-400 font-mono select-none')

        # Floating Controls Overlay (top-right)
        with ui.row().classes('fixed top-4 right-4 z-50 items-center gap-4 bg-slate-900/85 dark:bg-zinc-900/85 backdrop-blur-md px-4 py-2 rounded-lg border border-slate-800 dark:border-zinc-800 shadow-lg'):
            # Line Count Selector (Custom dark number input)
            lines_input = ui.number(
                label='Lines',
                value=DEFAULT_LINES,
                min=50,
                max=10000,
                format='%d',
                on_change=lambda: load_logs(scroll_to_bottom=True)
            ).props('outlined dense dark').classes('w-20')
            with lines_input:
                ui.tooltip('Lines to show')

            # Live Switch
            live_switch = ui.switch(
                'Live',
                value=True,
                on_change=lambda e: toggle_live(e.value)
            ).classes('text-xs text-slate-100 font-medium')
            with live_switch:
                ui.tooltip('Real-time live follow')

            # Wrap Switch (User selectable text-wrapping option)
            wrap_switch = ui.switch(
                'Wrap',
                value=False,
                on_change=lambda e: toggle_wrap(e.value)
            ).classes('text-xs text-slate-100 font-medium')
            with wrap_switch:
                ui.tooltip('Wrap long log lines')

            # Download Button (Triggers Dialog)
            download_btn = ui.button(
                icon='download',
                on_click=lambda: open_download_dialog()
            ).props('flat round color="white"').classes('text-white')
            with download_btn:
                ui.tooltip('Download log files')

        # Main Log Viewport (Native scrollbars on vertical and horizontal axes)
        log_scroll_area = ui.column().classes('w-full h-full bg-slate-950 p-4 font-mono text-xs overflow-auto flex-nowrap scrollbar-thin')
        with log_scroll_area:
            # pt-24 spacing ensures log content starts below the floating overlay headers!
            # w-max & min-w-full prevents row-wrapping and enables horizontal scrollbars perfectly.
            log_container = ui.column().classes('w-max min-w-full pt-24 pb-6 gap-0.5 whitespace-pre')

        def toggle_wrap(wrap_active: bool) -> None:
            """Toggle between horizontal scroll (whitespace-pre) and text-wrapping (whitespace-pre-wrap)."""
            if wrap_active:
                log_container.classes('w-full whitespace-pre-wrap', remove='w-max min-w-full whitespace-pre')
            else:
                log_container.classes('w-max min-w-full whitespace-pre', remove='w-full whitespace-pre-wrap')

        # Page state closures
        state = {
            'active_log_id': 'volttron.log',
            'loading': False,
            'lines': [],
            'end_offset': 0,
            'total_bytes': 0,
            'file_id': ''
        }

        import datetime

        def format_bytes(b: int) -> str:
            if not b:
                return '0 B'
            for unit in ['B', 'KB', 'MB', 'GB']:
                if b < 1024:
                    return f"{round(b)} {unit}" if b >= 10 or unit == 'B' else f"{b:.1f} {unit}"
                b /= 1024
            return f"{b:.1f} GB"

        def format_timestamp(ts: float) -> str:
            if not ts:
                return 'Unknown Time'
            try:
                dt = datetime.datetime.fromtimestamp(ts)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                return 'Unknown Time'

        def render_all_buffered() -> None:
            """Synchronously render currently buffered lines list."""
            log_container.clear()
            total_lines = len(state['lines'])
            with log_container:
                for i, line in enumerate(state['lines']):
                    escaped = html.escape(line)
                    level_class = _get_level_class(line)
                    
                    # If this is the very last line, show a bright green "LATEST" indicator in the gutter
                    if i == total_lines - 1:
                        num_span = '<span class="text-emerald-400 dark:text-emerald-400 select-none inline-block w-12 text-right mr-4 font-bold font-mono text-[9px] tracking-wider uppercase">LATEST</span>'
                        row_classes = 'w-full leading-relaxed bg-emerald-950/15 border-y border-emerald-900/30'
                    else:
                        num_span = f'<span class="text-slate-500 dark:text-zinc-500 select-none inline-block w-12 text-right mr-4 font-semibold font-mono">{i + 1}</span>'
                        row_classes = 'w-full leading-relaxed'

                    row_html = f'{num_span}<span class="{level_class}">{escaped}</span>'
                    ui.html(row_html, sanitize=False).classes(row_classes)
            
            file_size_label.set_text(
                f"retained: {len(state['lines'])} lines  "
                f"/  size: {format_bytes(state['total_bytes'])}"
            )

        async def load_logs(scroll_to_bottom: bool = False) -> None:
            """Fetch initial tail of active log file and display."""
            if state['loading']:
                return
            state['loading'] = True
            max_lines = int(lines_input.value or DEFAULT_LINES)

            try:
                # Retrieve the tail chunk from the platform web API
                # Scale requested byte size to line count (approx 256 bytes per line, capped at 1 MB)
                request_bytes = min(1048576, max_lines * 256)
                result = await agent_management.read_log_tail(instance, state['active_log_id'], max_lines, request_bytes)
                
                state['lines'] = result.get('lines', [])
                state['total_bytes'] = result.get('total_bytes', 0)
                state['end_offset'] = result.get('next_offset', state['total_bytes'])
                state['file_id'] = result.get('file_id', '')

                render_all_buffered()

                if scroll_to_bottom:
                    ui.timer(0.05, lambda: log_scroll_area.run_method('scrollTo', {'top': 99999999}), once=True)

                status_badge.set_text('Live' if live_switch.value else 'Paused')
                status_badge.props(f'color="{"green" if live_switch.value else "orange"}"')
            except Exception as e:
                status_badge.set_text(f'Read Error: {str(e)}')
                status_badge.props('color="red"')
            finally:
                state['loading'] = False

        # Live poll timer callback
        async def poll_callback() -> None:
            if not live_switch.value or state['loading']:
                return
            
            try:
                max_lines = int(lines_input.value or DEFAULT_LINES)
                # Fetch new lines from current end_offset forward
                result = await agent_management.read_log_after(instance, state['active_log_id'], state['end_offset'], CHUNK_BYTES)
                new_lines = result.get('lines', [])
                new_file_id = result.get('file_id', '')

                # Check if active file rotated
                if state['file_id'] and new_file_id and new_file_id != state['file_id']:
                    await load_logs(scroll_to_bottom=True)
                    return

                if new_lines:
                    state['lines'] = state['lines'] + new_lines
                    state['end_offset'] = result.get('next_offset', state['end_offset'])
                    state['total_bytes'] = result.get('total_bytes', state['total_bytes'])

                    # Enforce the rolling window cap
                    if len(state['lines']) > max_lines:
                        state['lines'] = state['lines'][-max_lines:]

                    render_all_buffered()
                    ui.timer(0.05, lambda: log_scroll_area.run_method('scrollTo', {'top': 99999999}), once=True)
                else:
                    # Update total size if it changed without lines (empty writes / padding)
                    state['total_bytes'] = result.get('total_bytes', state['total_bytes'])
                    render_all_buffered()
            except Exception:
                pass

        poll_timer = ui.timer(POLL_INTERVAL_SEC, poll_callback, active=True)

        def toggle_live(active: bool) -> None:
            poll_timer.active = active
            status_badge.set_text('Live' if active else 'Paused')
            status_badge.props(f'color="{"green" if active else "orange"}"')

        # ---- Download Dialog with real-time Progress Bar ---------------------
        with ui.dialog() as download_dialog, ui.card().classes('w-96 gap-4 p-5'):
            ui.label('Download Log File').classes('text-lg font-bold text-neutral-800 dark:text-neutral-100')
            
            # File selection
            file_select = ui.select(
                label='Select File',
                options={},
            ).props('outlined dense options-dense').classes('w-full')

            # Real-time Progress Bar Container (hidden initially)
            progress_container = ui.column().classes('w-full gap-2')
            with progress_container:
                progress_label = ui.label('Preparing...').classes('text-xs text-neutral-500 dark:text-neutral-400')
                progress_bar = ui.linear_progress(value=0.0).props('show-value track-color="grey-4" color="primary"')
            progress_container.visible = False

            # Actions row
            with ui.row().classes('w-full justify-end gap-2 border-t pt-3 border-neutral-100 dark:border-zinc-800'):
                cancel_btn = ui.button('Cancel', on_click=download_dialog.close).props('flat dense')
                download_confirm_btn = ui.button('Download', on_click=lambda: start_download()).props('unelevated dense color="primary"')

        async def open_download_dialog() -> None:
            """Fetch latest files list and open dialog."""
            try:
                info = await agent_management.list_log_info(instance)
                files = info.get('logs', [])
                if not files:
                    ui.notify('No log files available', type='warning')
                    return
                
                options = {}
                for f in files:
                    fid = f.get('id', '')
                    size = f.get('size_bytes', 0)
                    mtime = f.get('modified', 0)
                    mtime_str = format_timestamp(mtime) if mtime else 'Unknown'
                    options[fid] = f"{fid} ({format_bytes(size)} \u2022 Modified: {mtime_str})"

                file_select.options = options
                # Select the active log as default download
                file_select.value = state['active_log_id'] if state['active_log_id'] in options else files[0].get('id')

                # Reset dialog state
                progress_container.visible = False
                file_select.enable()
                download_confirm_btn.enable()
                cancel_btn.enable()
                
                download_dialog.open()
            except Exception as e:
                ui.notify(f'Failed to retrieve log files: {e}', type='negative')

        async def start_download() -> None:
            """Stream chunks from VUI and update progress bar in real-time."""
            selected_file = file_select.value
            if not selected_file:
                return

            # Find expected size from select label/metadata
            files_meta = await agent_management.list_log_info(instance)
            meta = next((f for f in files_meta.get('logs', []) if f.get('id') == selected_file), None)
            total_size_bytes = meta.get('size_bytes', 0) if meta else 0

            # Show progress bar and disable interaction
            progress_container.visible = True
            file_select.disable()
            download_confirm_btn.disable()
            cancel_btn.disable()

            try:
                chunks = []
                offset = 0
                max_chunk_bytes = 512 * 1024  # 512 KB chunks for maximum speed
                
                progress_label.set_text(f"Starting download of {selected_file}...")
                progress_bar.value = 0.0

                while True:
                    result = await agent_management.read_log_after(instance, selected_file, offset, max_chunk_bytes)
                    lines_chunk = result.get('lines', [])
                    next_offset = result.get('next_offset', offset)
                    file_total_bytes = result.get('total_bytes', total_size_bytes)
                    
                    if not lines_chunk:
                        break
                    
                    # Flatten chunk list back to bytes
                    chunk_text = '\n'.join(lines_chunk) + '\n'
                    chunks.append(chunk_text.encode('utf-8', errors='replace'))
                    
                    offset = next_offset
                    # Update progress
                    limit_size = file_total_bytes or total_size_bytes or 1
                    pct = clamp_progress(offset / limit_size)
                    progress_bar.value = pct
                    progress_label.set_text(f"Downloaded {format_bytes(offset)} / {format_bytes(limit_size)} ({round(pct*100)}%)")
                    
                    if next_offset >= file_total_bytes or next_offset <= offset:
                        break
                
                full_content = b''.join(chunks)
                if not full_content:
                    ui.notify('Log is empty, nothing to download', type='warning')
                    download_dialog.close()
                    return

                # Download file natively to user's local downloads folder
                ui.download(full_content, filename=selected_file)
                ui.notify(f"Download complete: {selected_file}", type='positive')
                download_dialog.close()
            except Exception as e:
                ui.notify(f"Download failed: {e}", type='negative')
                download_dialog.close()

        def clamp_progress(v: float) -> float:
            return max(0.0, min(1.0, v))

        async def init_page() -> None:
            # Detect what the active log file ID is (usually volttron.log)
            try:
                info = await agent_management.list_log_info(instance)
                files = info.get('logs', [])
                if files:
                    import re
                    active_candidate = next((f for f in files if not re.search(r'\.\d+$', f.get('id', ''))), files[0])
                    state['active_log_id'] = active_candidate.get('id', 'volttron.log')
            except Exception:
                pass
            await load_logs(scroll_to_bottom=True)

        ui.timer(0.1, init_page, once=True)
