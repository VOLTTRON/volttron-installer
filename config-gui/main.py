from dataclasses import dataclass
import os
from nicegui import ui

@dataclass
class Backer:
    data: str = ''
    option: str = ''

mybacker = Backer()

def filter_name(name):
    return name.replace("/", "|")

def create_config_file(name, config, format):
    save_path = os.getcwd() + "/configs/"
    # replace backslashes in name with pipes
    name = filter_name(name)
    # this ensures the file is saved to configs
    full_name = os.path.join(save_path, name+format)
    f = open(full_name, "w")
    f.write(config)
    f.close()

def add_config(identity, name):
    create_config_file(name, mybacker.data, mybacker.option)

def update_backer_json(data):
    setattr(mybacker, 'data', data)
    setattr(mybacker, 'option', '.json')

def update_backer_csv(data):
    setattr(mybacker, 'data', data)
    setattr(mybacker, 'option', '.csv')

def render_config_form():
    ui.label("Save a config").style("font-size: 20px")
    with ui.row():
        identity = ui.input(label="identity")
        name = ui.input(label="name")
    with ui.tabs() as tabs:
        one = ui.tab('json')
        two = ui.tab('csv')
    with ui.tab_panels(tabs, value=one).classes("w-full"):
        with ui.tab_panel(one):
            json = {}
            ui.json_editor({'content': {'json': json}}, 
                           on_change=lambda e: update_backer_json(e.content['text']))
        with ui.tab_panel(two):
            # ui.editor(on_change=lambda e: update_backer_csv(e.value))
            pass
    ui.button("Save Config", on_click=lambda: add_config(identity.value, name.value))

def render_config_list():
    columns = [
        {'name': 'config', 'label': 'Config', 'field': 'config', 'align': 'left'},
        {'name': 'platform', 'label': 'Platform', 'field': 'platform', 'align': 'left'},
    ]
    rows = [
        {'config': 'Config 1', 'platform': 'platform.driver'},
        {'config': 'Config 2', 'platform': 'platform.driver'},
    ]
    ui.link("Add to config", add_config_page)
    table = ui.table(columns=columns, rows=rows, row_key='config').classes('w-72')
    table.add_slot('header', r'''
        <q-tr :props="props">
            <q-th auto-width />
            <q-th v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.label }}
            </q-th>
        </q-tr>
    ''')
    table.add_slot('body', r'''
        <q-tr :props="props">
            <q-td auto-width>
                <q-btn size="sm" color="blue" round dense
                    @click="props.expand = !props.expand"
                    :icon="props.expand ? 'arrow_drop_up' : 'arrow_drop_down'" />
            </q-td>
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.value }}
            </q-td>
        </q-tr>
        <q-tr v-show="props.expand" :props="props">
            <q-td colspan="100%">
                <q-btn size="sm" color="blue" label="Edit" />
                <q-btn size="sm" color="red" label="Remove" />
            </q-td>
        </q-tr>
    ''')

@ui.page('/new-config')
def add_config_page():
    ui.link("Back to list", config_list_page)
    render_config_form()

@ui.page('/')
def config_list_page():
    render_config_list()

def main():
    config_list_page()
    ui.run()

main()