import io
import zipfile

from nicegui import binding, ui

import src.db as db
from src import theme
from src.manage_instances import config_store
from src.manage_instances.config_templates import TEMPLATES


def _uploaded_config_type(filename: str) -> str:
    lower_name = filename.lower()
    if lower_name.endswith(('.json', '.config')):
        return 'application/json'
    if lower_name.endswith('.csv'):
        return 'text/csv'
    return 'text/plain'


def _uploaded_config_name(filename: str, agent_identity: str) -> str:
    clean_name = filename.replace('\\', '/').split('/')[-1]
    lower_name = clean_name.lower()
    if agent_identity == 'platform.driver' and lower_name.endswith('.config'):
        return f"devices/{clean_name.rsplit('.', 1)[0]}"
    return clean_name


def _uploaded_config_entries(filename: str, content: bytes, agent_identity: str) -> list[tuple[str, str, str]]:
    lower_name = filename.lower()
    if lower_name.endswith('.zip'):
        entries: list[tuple[str, str, str]] = []
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                member_name = member.filename.replace('\\', '/').split('/')[-1]
                if not member_name or member_name.lower().endswith('readme.txt'):
                    continue
                content_type = _uploaded_config_type(member_name)
                if content_type not in {'application/json', 'text/csv', 'text/plain'}:
                    continue
                text = archive.read(member).decode('utf-8-sig')
                entries.append((_uploaded_config_name(member_name, agent_identity), text, content_type))
        return entries

    return [(
        _uploaded_config_name(filename, agent_identity),
        content.decode('utf-8-sig'),
        _uploaded_config_type(filename),
    )]


def render(instance_name: str, agent_identity: str):
    dark_mode = theme.dark_mode()
    instances = db.get_instances()
    instance = next((i for i in instances if i.get('name') == instance_name), None)

    if not instance:
        with ui.column().classes('w-full items-center py-20'):
            ui.label(f'Instance "{instance_name}" not found').classes('text-red-500 text-2xl font-bold mb-4')
            back_btn = ui.button('Back to Instances', icon='arrow_back', on_click=lambda: ui.navigate.to('/instances')).props('outline')
            binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
        return

    selected_config = None
    config_names_container = None
    config_name_input = None
    config_type_select = None

    json_editor = None
    text_editor = None
    editor_errors = {}
    current_json_content = {}   # live content pushed from json_editor on_change
    is_dirty = False             # True when unsaved changes exist

    save_button = None
    delete_button = None
    status_label = None

    def refresh_save_button():
        """Update the save button's label and enabled state based on mode and dirty flag."""
        if save_button is None:
            return
        if selected_config is not None and not is_dirty:
            # Viewing an existing config, no pending changes — disable to prevent no-op saves
            save_button.set_text('Save Config')
            save_button.props('icon=save')
            save_button.disable()
        elif selected_config is not None and is_dirty:
            # Editing an existing config with unsaved changes
            save_button.set_text('Update Config')
            save_button.props('icon=save_as')
            save_button.enable()
        else:
            # Creating a new config (no selected_config)
            save_button.set_text('Save Config')
            save_button.props('icon=save')
            save_button.enable()

    async def load_configs():
        if config_names_container is None:
            return
        config_names_container.clear()
        try:
            names = await config_store.list_configs(instance, agent_identity)
        except Exception as e:
            with config_names_container:
                ui.label(f'Could not load configs: {e}').classes('text-negative')
            return

        with config_names_container:
            if not names:
                ui.label('No configs stored for this agent.').classes('text-grey-6')
                return

            for name in names:
                async def select_config(config_name=name):
                    nonlocal selected_config, editor_errors, is_dirty
                    selected_config = config_name
                    editor_errors = {}
                    is_dirty = False
                    try:
                        content, content_type = await config_store.get_config(instance, agent_identity, config_name)
                        config_name_input.value = config_name
                        content_type = content_type if content_type in ['application/json', 'text/csv', 'text/plain'] else 'application/json'
                        config_type_select.value = content_type
                        set_editor_value(content, content_type)
                        update_editor_visibility(content_type)
                        delete_button.enable()
                        refresh_save_button()
                        status_label.set_text(f'Editing {config_name}')
                    except Exception as e:
                        ui.notify(f'Failed to load config: {e}', type='negative')

                ui.button(name, icon='description', on_click=select_config).props('flat align="left"').classes('w-full justify-start')

    def get_editor_value() -> str:
        if config_type_select.value == 'application/json':
            # Prefer live content from the on_change event (user edits in browser).
            # Fall back to the last server-pushed properties only when no change has
            # been received yet (e.g. immediately after programmatic load).
            content = current_json_content or (json_editor.properties.get('content', {}) if json_editor else {})
            if 'json' in content:
                import json
                return json.dumps(content['json'], indent=2)
            elif 'text' in content:
                return content['text']
            return '{}'
        else:
            return text_editor.value or '' if text_editor else ''

    def set_editor_value(value: str, content_type: str):
        nonlocal current_json_content
        if content_type == 'application/json':
            try:
                import json
                parsed = json.loads(value)
                pushed = {'json': parsed}
                if json_editor:
                    json_editor.properties['content'] = pushed
                current_json_content = pushed
            except Exception:
                pushed = {'text': value}
                if json_editor:
                    json_editor.properties['content'] = pushed
                current_json_content = pushed
            if json_editor:
                json_editor.update()
            if text_editor:
                text_editor.value = value
        else:
            if text_editor:
                text_editor.value = value
            try:
                import json
                parsed = json.loads(value)
                pushed = {'json': parsed}
                if json_editor:
                    json_editor.properties['content'] = pushed
                current_json_content = pushed
            except Exception:
                pushed = {'text': value}
                if json_editor:
                    json_editor.properties['content'] = pushed
                current_json_content = pushed
            if json_editor:
                json_editor.update()

    def update_editor_visibility(content_type: str):
        if content_type == 'application/json':
            if text_editor and json_editor:
                raw_val = text_editor.value or ''
                try:
                    import json
                    parsed = json.loads(raw_val)
                    json_editor.properties['content'] = {'json': parsed}
                except Exception:
                    json_editor.properties['content'] = {'text': raw_val}
                json_editor.update()
            if json_editor:
                json_editor.set_visibility(True)
            if text_editor:
                text_editor.set_visibility(False)
        else:
            if json_editor and text_editor:
                content = json_editor.properties.get('content', {})
                if 'json' in content:
                    import json
                    text_editor.value = json.dumps(content['json'], indent=2)
                elif 'text' in content:
                    text_editor.value = content['text']
            if json_editor:
                json_editor.set_visibility(False)
            if text_editor:
                text_editor.set_visibility(True)

    def clear_editor():
        nonlocal selected_config, editor_errors, is_dirty
        selected_config = None
        editor_errors = {}
        is_dirty = False
        config_name_input.value = ''
        config_type_select.value = 'application/json'
        set_editor_value('{}', 'application/json')
        update_editor_visibility('application/json')
        delete_button.disable()
        refresh_save_button()
        status_label.set_text('Creating new config')

    async def save_config():
        nonlocal selected_config, is_dirty
        config_name = (config_name_input.value or '').strip()
        if not config_name:
            ui.notify('Config name is required', type='warning')
            return

        content_type = config_type_select.value
        if content_type == 'application/json':
            if editor_errors:
                ui.notify('Cannot save: JSON has validation or syntax errors', type='negative')
                return
            content_str = get_editor_value()
            try:
                import json
                json.loads(content_str)
            except Exception as e:
                ui.notify(f'Cannot save: Invalid JSON syntax ({e})', type='negative')
                return
        else:
            content_str = get_editor_value()

        overwrite = selected_config == config_name
        try:
            await config_store.save_config(
                instance,
                agent_identity,
                config_name,
                content_str,
                content_type,
                overwrite=overwrite,
            )
            selected_config = config_name
            is_dirty = False
            delete_button.enable()
            refresh_save_button()
            status_label.set_text(f'Editing {config_name}')
            ui.notify('Config saved', type='positive')
            await load_configs()
        except Exception as e:
            ui.notify(f'Failed to save config: {e}', type='negative')

    async def upload_config_file(event):
        try:
            content = await event.file.read()
            entries = _uploaded_config_entries(event.file.name, content, agent_identity)
            if not entries:
                ui.notify('No supported config files found in upload', type='warning')
                return

            for config_name, config_content, content_type in entries:
                await config_store.save_config(
                    instance,
                    agent_identity,
                    config_name,
                    config_content,
                    content_type,
                    overwrite=True,
                )

            ui.notify(f'Imported {len(entries)} config entr{"y" if len(entries) == 1 else "ies"}', type='positive')
            await load_configs()
        except Exception as e:
            ui.notify(f'Failed to import config: {e}', type='negative')

    async def delete_selected_config():
        nonlocal selected_config
        if not selected_config:
            return
        try:
            await config_store.delete_config(instance, agent_identity, selected_config)
            ui.notify(f'Deleted {selected_config}', type='positive')
            clear_editor()
            await load_configs()
        except Exception as e:
            ui.notify(f'Failed to delete config: {e}', type='negative')

    async def delete_all_agent_configs():
        with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4 min-w-96'):
            ui.label(f'Delete all configs for {agent_identity}?').classes('text-lg font-bold text-negative')
            ui.label('This removes every configuration entry for this agent from the VOLTTRON config store.')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Cancel', on_click=confirm_dialog.close).props('flat')

                async def confirm_delete_all():
                    confirm_dialog.close()
                    try:
                        await config_store.delete_all_configs(instance, agent_identity)
                        ui.notify('All configs deleted', type='positive')
                        clear_editor()
                        await load_configs()
                    except Exception as e:
                        ui.notify(f'Failed to delete configs: {e}', type='negative')

                ui.button('Delete All', icon='delete_sweep', on_click=confirm_delete_all).props('color="negative"')
        confirm_dialog.open()

    with ui.column().classes('w-full items-center py-8 px-4 gap-5'):
        with ui.column().classes('w-full max-w-6xl gap-4'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-3'):
                    back_btn = ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to(f'/manage/{instance_name}')).props('flat round')
                    binding.bind_from(back_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'white' if val else 'primary')
                    with ui.column().classes('gap-0'):
                        ui.label('Config Store').classes('text-3xl font-bold')
                        ui.label(f'{instance_name} / {agent_identity}').classes('text-grey-6')

                theme_btn = ui.button(on_click=dark_mode.toggle).props('flat round')
                theme_btn.bind_icon_from(dark_mode, 'value', backward=lambda val: 'light_mode' if val else 'dark_mode')
                binding.bind_from(theme_btn._props, 'color', dark_mode, 'value', backward=lambda val: 'warning' if val else 'primary')

            ui.separator()

            with ui.row().classes('w-full gap-5 items-stretch no-wrap'):
                with ui.column().classes('gap-3 py-2 w-80 min-w-80'):
                    ui.label('Add Configs').classes('font-bold')
                    ui.button('Blank Config', icon='add', on_click=clear_editor).props('outline color="primary"').classes('w-full')
                    import_upload = ui.upload(
                        label='Import Config Files',
                        auto_upload=True,
                        multiple=True,
                        on_upload=upload_config_file,
                    ).props('accept=".json,.config,.csv,.txt,.zip"').classes('hidden')
                    ui.button('Import Files', icon='upload').props('outline color="primary"').classes('w-full').on(
                        'click',
                        js_handler=f'() => getElement("{import_upload.id}").$refs.qRef.pickFiles()',
                    )
                    ui.separator()
                    ui.label('Templates').classes('font-bold')
                    
                    def apply_template(template_name):
                        nonlocal selected_config, is_dirty
                        if not template_name:
                            return
                        template = TEMPLATES[template_name]
                        # Applying a template starts a new entry — clear any existing selection
                        selected_config = None
                        is_dirty = False
                        config_name_input.value = template["name"]
                        config_type_select.value = template["type"]

                        import json
                        content = template["content"]
                        content_str = content if isinstance(content, str) else json.dumps(content, indent=2)
                        set_editor_value(content_str, template["type"])
                        update_editor_visibility(template["type"])
                        delete_button.disable()
                        refresh_save_button()
                        status_label.set_text('Creating new config')

                        template_select.value = None
                        ui.notify(f"Applied template: {template_name}", type="info")

                    template_select = ui.select(
                        options=list(TEMPLATES.keys()),
                        label='Insert Template',
                        on_change=lambda e: apply_template(e.value)
                    ).props('outlined dense').classes('w-full')
                    
                    ui.separator()
                    ui.label('Stored Configs').classes('font-bold')
                    config_names_container = ui.column().classes('w-full gap-1 min-h-80')
                    ui.space()
                    ui.button('Delete All Configs', icon='delete_sweep', on_click=delete_all_agent_configs).props('outline color="negative"').classes('w-full')

                ui.separator().props('vertical')

                with ui.column().classes('gap-3 py-2 flex-grow min-w-0'):
                    with ui.row().classes('w-full justify-between items-center'):
                        status_label = ui.label('Creating new config').classes('text-grey-6')
                        with ui.row().classes('gap-2'):
                            delete_button = ui.button('Delete Config', icon='delete', on_click=delete_selected_config).props('outline color="negative"')
                            save_button = ui.button('Save Config', icon='save', on_click=save_config).props('color="primary"')
                            delete_button.disable()

                    with ui.row().classes('w-full gap-3 no-wrap'):
                        config_name_input = ui.input('Config Name', placeholder='e.g. devices/campus/building/fake').props('outlined dense').classes('flex-grow')
                        config_type_select = ui.select(
                            {
                                'application/json': 'JSON',
                                'text/csv': 'CSV',
                                'text/plain': 'Raw Text',
                            },
                            value='application/json',
                            label='Content Type',
                            on_change=lambda e: update_editor_visibility(e.value),
                        ).props('outlined dense').classes('w-44')
                    ui.label('Device configurations for drivers typically require the "devices/" prefix.').classes('text-grey-6 text-xs')
                    
                    with ui.column().classes('w-full flex-auto min-h-96') as editor_container:
                        def handle_json_change(e):
                            nonlocal editor_errors, current_json_content, is_dirty
                            editor_errors = e.errors
                            current_json_content = e.content   # live content from browser
                            is_dirty = True
                            refresh_save_button()

                        json_editor = ui.json_editor(
                            properties={'content': {'json': {}}, 'mode': 'tree'},
                            on_change=handle_json_change,
                        ).classes('w-full flex-auto min-h-96')

                        def handle_text_change(_=None):
                            nonlocal is_dirty
                            is_dirty = True
                            refresh_save_button()

                        text_editor = ui.textarea('Content', value='', on_change=handle_text_change).props('outlined').classes('w-full flex-auto min-h-96 font-mono')
                        text_editor.set_visibility(False)

    ui.timer(0.1, load_configs, once=True)
