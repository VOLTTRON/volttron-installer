from datetime import datetime
from nicegui import ui
from typing import Dict, List, Optional

import csv
import json
import os

from new_volttron_installer.classes import Backer

mybacker = Backer()

new_column_start = 4

def update_backer_json(data):
    setattr(mybacker, 'data', data)
    setattr(mybacker, 'option', '.json')

def save_json_config(file_name: str, config_name: str, config: Dict, agent: str):
    file_path = os.path.expanduser(f"~/.volttron_installer/platforms/configs/{file_name}.json")
    
    # Create metadata so program knows what agent the file is for
    metadata = {
        "name": config_name,
        "agent": agent,
        "date": str(datetime.now())
    }

    full_config = {
        "metadata": metadata,
        "config": config
        }

    with open(file_path, "w") as config_file:
        json.dump(full_config, config_file, indent=2)

def save_csv_config(file_name: str, config_name: str, config: List, agent: str):
    data = []

    # Create metadata so program knows what agent the file is for
    metadata = {
        "name": config_name,
        "agent": agent,
        "date": str(datetime.now())
    }
    
    file_path = os.path.expanduser(f"~/.volttron_installer/platforms/configs/{file_name}.csv")
    for row in config:
        data.append(list(row.values()))

    with open(file_path, 'w', newline='') as config_file:
        writer = csv.writer(config_file)

        for key, value in metadata.items():
            writer.writerow([f"# {key}: {value}"])
        
        writer.writerow([])
        writer.writerows(data)
        
def render_config_form():
    data = [
        {"point_name": "", "modbus_reg": "", "writable": "", "point_address": ""}
    ]

    columns = [
        {"headerName": "Volttron Point Name", "field": "point_name", "editable": True},
        {"headerName":"Modbus Register", "field": "modbus_reg", "editable": True},
        {"headerName": "Writable", "field": "writable", "editable": True},
        {"headerName": "Point Address", "field": "point_address", "editable": True}
    ]

    preset_list = ["None", "Bacnet", "DNP3", "Inverter Sample", "Catalyst"]

    def update_data_from_table_change(e):
        data[e.args["rowIndex"]] = e.args["data"]

    def new_row():
        row_dict = {}
        for col in columns:
            row_dict.update({col["field"]: ""})
        data.append(row_dict)
        table.update()

    def new_column():
        global new_column_start
        new_column = {"field": f'col {new_column_start}', "editable": True}
        columns.append(new_column)

        # update each row with new column
        for row in data:
            row.update({f'col {new_column_start}': ""})

        new_column_start += 1
        table.update()

    async def delete_selected():
        selected_rows = await table.get_selected_rows()
        data[:] = [row for row in data if row not in selected_rows]
        table.update()

    def handle_preset_choice(choice):
        if choice == "Bacnet":
            pass

    ui.label("Save a config").style("font-size: 20px")
    with ui.row():
        agent = ui.input(label="Agent Identity", validation={"Please add an identity.": lambda value: len(value) != 0})
        config_name = ui.input(label="Configuration Name", validation={"Please add a configuration name.": lambda value: len(value) != 0})
        file_name = ui.input(label="File Name", validation={"Please add a file name.": lambda value: len(value) != 0})
    with ui.tabs() as tabs:
        one = ui.tab('json')
        two = ui.tab('csv')
    with ui.tab_panels(tabs, value=two).classes("w-full"):
        with ui.tab_panel(one):
            json = {}
            ui.json_editor({'content': {'json': json}}, 
                           on_change=lambda e: (update_backer_json(e.content['json'])))
            ui.button("Save Config", on_click=lambda: save_json_config(file_name.value, config_name.value, mybacker.data, agent.value))
        with ui.tab_panel(two):
            with ui.row():
                ui.button("Add row", on_click=new_row, color="secondary")
                ui.button("Add column", on_click=new_column, color="secondary")
                ui.button("Delete selected row", on_click=delete_selected, color="red")
                ui.select(options=preset_list, 
                         label="Select a preset (optional)", value=preset_list[0], 
                         on_change=lambda e: handle_preset_choice(e.value)).classes("w-full")
            table = ui.aggrid({
                "columnDefs": columns,
                "rowData": data,
                "rowSelection": "multiple",
                "stopEditingWhenCellsLoseFocus": True,
            }).on("cellValueChanged", update_data_from_table_change)
            ui.button("Save Config", on_click=lambda: save_csv_config(file_name.value, config_name.value, data, agent.value))

@ui.page('/edit/config/')
def show_config():
    ui.link("Back to list", ui.open("http://127.0.0.1:8080/config"))
    render_config_form()