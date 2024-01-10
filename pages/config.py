from datetime import datetime
from nicegui import ui
from typing import Dict, List

import csv
import json
import os


new_column_start = 4

# Remove configuration and delete file associated; Not done
def remove_configuration(configuration: str):
    print(configuration)

# Redirect to edit config page; Not done
def edit_configuration_redirect(configuration: str):
    print(configuration)

def render_config_list(rows: List[Dict]):
    columns = [
        {'name': 'config_name', 'label': 'Configuration Name', 'field': 'config_name', 'align': 'left'},
        {'name': 'agent_identity', 'label': 'Agent Identity', 'field': 'agent_identity', 'align': 'left'},
    ]

    table = ui.table(columns=columns, rows=rows, row_key='config', selection="single").classes('w-72')
    
    with ui.row().bind_visibility_from(table, "selected", backward=lambda val: bool(val)):
        ui.button("Edit", on_click=lambda: edit_configuration_redirect(label.text))
        ui.button("Remove", on_click=lambda: remove_configuration(label.text))

    with ui.row():
        ui.label("Current Selection:").bind_visibility_from(table, 'selected', backward=lambda val: bool(val))
        label = ui.label().bind_text_from(table, "selected", lambda val: str(val)).bind_visibility_from(table, 'selected', backward=lambda val: bool(val))

@ui.page('/config')
def show_config_list():
    '''Shows list of configurations'''
    ui.button("Add to config", on_click=lambda: ui.open("http://127.0.0.1:8080/edit/config/"))
    rows = []
    if os.path.exists(os.path.expanduser("~/.volttron_installer/platforms/configs")):
        if os.listdir(os.path.expanduser("~/.volttron_installer/platforms/configs/")):
            for file in os.listdir(os.path.expanduser("~/.volttron_installer/platforms/configs/")):
                if ".json" in file:
                    with open(os.path.expanduser(f"~/.volttron_installer/platforms/configs/{file}"), 'r') as config_file:
                        config_dict = json.load(config_file)
                        rows.append({"config_name": config_dict["metadata"]["name"], "agent_identity": config_dict["metadata"]["agent"]})
                
                # Need to parse configuration name and agent identity from .csv file; Find how the files are saved in edit_config.py
                if ".csv" in file:
                    with open(os.path.expanduser(f"~/.volttron_installer/platforms/configs/{file}"), 'r', newline='') as config_file:
                        reader = csv.reader(config_file)
                        for row in reader:
                            print(row)
                            if 'name:' in row:
                                config_name = (row[0].split(":"))[1].strip()
                                print(config_name)
                            elif 'agent:' in row:
                                agent_identity = (row[0].split(":"))[1].strip()
                                print(agent_identity)

    render_config_list(rows)
