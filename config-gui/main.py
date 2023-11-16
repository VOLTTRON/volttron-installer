from dataclasses import dataclass
import os
from nicegui import ui

@dataclass
class Backer:
    data: str = ''
    option: str = ''

mybacker = Backer()

def create_config_file(config, option):
    if option == "json":
        f = open("test.config", "w")
    else:
        f = open("test.csv", "w")

    f.write(config)
    f.close()

def add_config(identity, name):
    # write/create config file
    #create_config_file(mybacker.data, mybacker.option)
    # get path to config file
    # if mybacker.option == "json":
    #     config_path = os.getcwd() + "/test.config"
    # else:
    #     config_path = os.getcwd() + "/test.csv"
    print(f'identity: {identity}, name: {name}')
    print(f'config: {mybacker.data}, option: {mybacker.option}')

def update_backer_json(data):
    setattr(mybacker, 'data', data)
    setattr(mybacker, 'option', 'json')

def render_config_form():
    ui.label("Save a config").style("font-size: 20px")
    with ui.row():
        identity = ui.input(label="identity")
        name = ui.input(label="name")
    with ui.tabs() as tabs:
        one = ui.tab('json')
        two = ui.tab('csv')
    with ui.tab_panels(tabs, value=one):
        with ui.tab_panel(one):
            json = {}
            ui.json_editor({'content': {'json': json}}, 
                           on_change=lambda e: update_backer_json(e.content['text']))
        with ui.tab_panel(two):
            ui.label('Second tab')
    ui.button("Save Config", on_click=lambda: add_config(identity.value, name.value))

@ui.page('/new-config')
def add_config_page():
    ui.link("Back to list", config_list_page)
    render_config_form()

@ui.page('/')
def config_list_page():
    columns = [
        {'name': 'config', 'label': 'Config', 'field': 'config', 'align': 'left'},
        {'name': 'platform', 'label': 'Platform', 'field': 'platform', 'align': 'left'},
    ]
    rows = [
        {'config': 'Config 1', 'platform': 'platform.driver'},
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

def main():
    config_list_page()
    ui.run()

main()