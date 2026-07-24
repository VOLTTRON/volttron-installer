import html
import re
from urllib.parse import quote

from nicegui import ui

import volttron_installer.db as db
from volttron_installer.dark import dark_mode_control
from volttron_installer.manage_instances import agent_management


INITIAL_LOG_BYTES = 65536
HISTORY_LOG_BYTES = 131072
LIVE_LOG_BYTES = 65536
MAX_DISPLAY_LINES = 1000

# TODO: Add server-side time/search indexing and direct cursor jumps before supporting
# multi-gigabyte retention; sequential 128 KiB history paging is intentionally simple
# and bounded, but is not suitable for navigating very large archives.


def log_content(lines: list[str]) -> str:
    entries = lines or ['Log is empty.']
    return ''.join(f'<div>{html.escape(line)}</div>' for line in entries)


def _rotation_logs(logs: list[dict]) -> list[dict]:
    active = next((log for log in logs if log.get('id') == 'volttron.log'), None)
    if not active:
        return []
    base_name = active['id']
    rotations = [
        log for log in logs
        if log.get('id') == base_name or re.fullmatch(re.escape(base_name) + r'\.\d+', log.get('id', ''))
    ]
    return sorted(rotations, key=lambda log: int(log['id'].rsplit('.', 1)[1]) if log['id'] != base_name else 0)


def _bounded_lines(lines: list[str], keep: str = 'newest') -> list[str]:
    if len(lines) <= MAX_DISPLAY_LINES:
        return lines
    if keep == 'oldest':
        return lines[:MAX_DISPLAY_LINES]
    return lines[-MAX_DISPLAY_LINES:]


def render(instance_name: str):
    dark_mode_control()
    instance = next((item for item in db.get_instances() if item.get('name') == instance_name), None)
    if not instance:
        with ui.column().classes('w-full items-center py-20'):
            ui.label(f'Instance "{instance_name}" not found').classes('text-red-500 text-2xl font-bold mb-4')
            ui.button('Back to Instances', icon='arrow_back', on_click=lambda: ui.navigate.to('/instances')).props('outline')
        return

    rotations: list[dict] = []
    lines: list[str] = []
    oldest_log_id = 'volttron.log'
    oldest_offset = 0
    live_log_id = 'volttron.log'
    live_offset = 0
    live_file_id = None
    loading = False
    following = True
    updating_live_switch = False

    def rotation_index(log_id: str) -> int | None:
        return next((index for index, log in enumerate(rotations) if log['id'] == log_id), None)

    def set_status(text: str, color: str = 'text-grey-6'):
        status_label.set_text(text)
        status_label.classes(replace=f'text-sm {color}')

    def format_bytes(value: int) -> str:
        if value < 1024:
            return f'{value} B'
        if value < 1024 * 1024:
            return f'{value / 1024:.0f} KiB'
        return f'{value / (1024 * 1024):.1f} MiB'

    def older_bytes_available() -> int:
        index = rotation_index(oldest_log_id)
        archived_bytes = sum(log['size_bytes'] for log in rotations[index + 1:]) if index is not None else 0
        return oldest_offset + archived_bytes

    def update_context(prefix: str):
        older_bytes = older_bytes_available()
        if older_bytes:
            context_label.set_text(
                f'{prefix} · oldest visible: {oldest_log_id} at {format_bytes(oldest_offset)} · '
                f'{format_bytes(older_bytes)} older available'
            )
        else:
            context_label.set_text(f'{prefix} · oldest retained entry reached')

    def render_lines(scroll_to_bottom: bool = False):
        log_view.set_content(log_content(lines))
        count_label.set_text(f'{len(lines):,} lines shown · {MAX_DISPLAY_LINES:,}-line limit')
        if scroll_to_bottom:
            log_view.run_method('scrollTo', 0, 1_000_000_000)

    def set_live_switch(value: bool):
        nonlocal updating_live_switch
        if live_switch.value == value:
            return
        updating_live_switch = True
        live_switch.set_value(value)
        updating_live_switch = False

    async def discover_logs():
        nonlocal rotations
        log_info = await agent_management.list_log_info(instance)
        rotations = _rotation_logs(log_info['logs'])
        retention = log_info.get('retention')
        if retention:
            total_mib = retention['max_total_bytes'] / (1024 * 1024)
            retention_info.tooltip(
                f'Up to {total_mib:g} MiB may be retained across the active log and '
                f"{retention['backup_count']} rotated files."
            )
        if not rotations:
            raise agent_management.PlatformCommandError('No rotating VOLTTRON logs are available.')

    async def jump_to_latest():
        nonlocal lines, oldest_log_id, oldest_offset, live_log_id, live_offset, live_file_id
        nonlocal loading, following
        if loading:
            return
        loading = True
        try:
            await discover_logs()
            page = await agent_management.read_log_before(
                instance, 'volttron.log', 2**63 - 1, INITIAL_LOG_BYTES,
            )
            lines = _bounded_lines(page.get('lines', []))
            oldest_log_id = page['log_id']
            oldest_offset = page.get('start_offset', 0)
            live_log_id = page['log_id']
            live_offset = page.get('end_offset', page.get('total_bytes', 0))
            live_file_id = page.get('file_id')
            following = True
            set_live_switch(True)
            load_older_button.set_enabled(oldest_offset > 0 or len(rotations) > 1)
            jump_latest_button.set_enabled(False)
            set_status('Live', 'text-positive')
            update_context('Latest window')
            render_lines(scroll_to_bottom=True)
        except Exception as exc:
            set_status('Disconnected', 'text-negative')
            ui.notify(f'Could not load logs: {exc}', type='negative')
        finally:
            loading = False

    async def load_older():
        nonlocal lines, oldest_log_id, oldest_offset, loading, following
        if loading:
            return
        loading = True
        following = False
        set_live_switch(False)
        load_older_button.set_text('Loading older logs...')
        load_older_button.disable()
        try:
            index = rotation_index(oldest_log_id)
            if index is None:
                await discover_logs()
                index = rotation_index(oldest_log_id)
            if oldest_offset > 0:
                page = await agent_management.read_log_before(
                    instance, oldest_log_id, oldest_offset, HISTORY_LOG_BYTES,
                )
            elif index is not None and index < len(rotations) - 1:
                await discover_logs()
                index = rotation_index(oldest_log_id)
                if index is None or index >= len(rotations) - 1:
                    return
                older_file = rotations[index + 1]
                page = await agent_management.read_log_before(
                    instance, older_file['id'], older_file['size_bytes'], HISTORY_LOG_BYTES,
                )
            else:
                return

            added = page.get('lines', [])
            lines = _bounded_lines(added + lines, keep='oldest')
            oldest_log_id = page['log_id']
            oldest_offset = page.get('start_offset', 0)
            index = rotation_index(oldest_log_id)
            has_older_file = index is not None and index < len(rotations) - 1
            load_older_button.set_enabled(oldest_offset > 0 or has_older_file)
            jump_latest_button.set_enabled(True)
            set_status('Viewing older logs')
            update_context(
                f"Loaded {len(added):,} older lines from {page['log_id']} "
                f"({format_bytes(page.get('start_offset', 0))}-{format_bytes(page.get('end_offset', 0))})"
            )
            render_lines()
            log_view.run_method('scrollTo', 0, 0)
        except Exception as exc:
            ui.notify(f'Could not load older entries: {exc}', type='negative')
        finally:
            load_older_button.set_text('Show older logs')
            index = rotation_index(oldest_log_id)
            has_older_file = index is not None and index < len(rotations) - 1
            load_older_button.set_enabled(oldest_offset > 0 or has_older_file)
            loading = False

    async def poll_live():
        nonlocal lines, live_log_id, live_offset, live_file_id, loading
        if loading or not following:
            return
        loading = True
        try:
            result = await agent_management.read_log_after(
                instance, live_log_id, live_offset, LIVE_LOG_BYTES,
            )
            replaced = live_file_id and result.get('file_id') != live_file_id
            if replaced or result.get('total_bytes', 0) < live_offset:
                await discover_logs()
                rotated = next((log for log in rotations[1:] if log.get('file_id') == live_file_id), None)
                if rotated:
                    live_log_id = rotated['id']
                    result = await agent_management.read_log_after(
                        instance, live_log_id, live_offset, LIVE_LOG_BYTES,
                    )
                else:
                    loading = False
                    await jump_to_latest()
                    return

            additions = result.get('lines', [])
            live_offset = result.get('next_offset', live_offset)
            live_file_id = result.get('file_id', live_file_id)
            if additions:
                lines = _bounded_lines(lines + additions)
                update_context('Latest window')
                render_lines(scroll_to_bottom=True)

            if live_log_id != 'volttron.log' and live_offset >= result.get('total_bytes', 0):
                live_log_id = 'volttron.log'
                live_offset = 0
                live_file_id = next(
                    (log.get('file_id') for log in rotations if log['id'] == 'volttron.log'),
                    None,
                )
        except Exception as exc:
            set_status('Live update failed', 'text-negative')
            ui.notify(f'Could not update logs: {exc}', type='negative')
        finally:
            loading = False

    async def toggle_live(event):
        nonlocal following
        if updating_live_switch:
            return
        following = bool(event.value)
        if following:
            await jump_to_latest()
        else:
            jump_latest_button.set_enabled(True)
            set_status('Paused')

    def handle_scroll(event):
        nonlocal following
        if not following or not isinstance(event.args, dict):
            return
        values = list(event.args.values())
        if len(values) != 3:
            return
        scroll_top, scroll_height, client_height = (float(value or 0) for value in values)
        if scroll_height - scroll_top - client_height > 80:
            following = False
            set_live_switch(False)
            jump_latest_button.set_enabled(True)
            set_status('Paused')

    with ui.column().classes('w-full min-h-screen p-3 md:p-5 gap-3'):
        with ui.row().classes('w-full items-center justify-between gap-3 flex-wrap'):
            with ui.row().classes('items-center gap-2'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to(f'/manage/{quote(instance_name, safe="")}')).props('flat round')
                with ui.column().classes('gap-0'):
                    ui.label('Platform Logs').classes('text-2xl font-bold')
                    ui.label(instance_name).classes('text-grey-6')
            with ui.row().classes('items-center gap-2'):
                status_label = ui.label('Connecting...').classes('text-sm text-grey-6')
                retention_info = ui.icon('info_outline', color='grey').classes('cursor-help')
                ui.button(icon='refresh', on_click=jump_to_latest).props('flat round').tooltip('Reload the latest log entries')

        with ui.row().classes(
            'sticky top-0 z-20 w-full items-center justify-between gap-2 flex-wrap '
            'bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded shadow-sm p-2'
        ):
            load_older_button = ui.button('Show older logs', icon='expand_less', on_click=load_older).props('outline no-caps')
            load_older_button.tooltip(f'Load up to {HISTORY_LOG_BYTES // 1024} KiB preceding the oldest visible entry')
            count_label = ui.label(f'0 lines shown · {MAX_DISPLAY_LINES:,}-line limit').classes('text-xs text-grey-6')
            with ui.row().classes('items-center gap-2'):
                jump_latest_button = ui.button('Jump to latest', icon='vertical_align_bottom', on_click=jump_to_latest).props('flat no-caps color="primary"')
                live_switch = ui.switch('Live', value=True, on_change=toggle_live).props('dense color="positive"')

        context_label = ui.label('Loading the latest log window...').classes('w-full text-xs text-grey-6 px-1')

        log_view = ui.html('', sanitize=False).classes(
            'w-full flex-1 min-h-96 m-0 p-3 md:p-4 bg-slate-950 border border-slate-700 rounded '
            'text-slate-100 font-mono text-xs md:text-sm leading-6 overflow-auto shadow-inner'
        )
        log_view.style('height: calc(100vh - 11rem); white-space: pre-wrap; overflow-wrap: anywhere;')
        log_view.on(
            'scroll', handle_scroll,
            ['target.scrollTop', 'target.scrollHeight', 'target.clientHeight'],
            throttle=0.2,
        )

    ui.timer(0.1, jump_to_latest, once=True)
    ui.timer(5.0, poll_live)
