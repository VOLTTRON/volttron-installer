from nicegui import ui
from shutil import rmtree
from typing import List
from urllib.parse import urlparse
from yaml import dump, safe_load

import json
import os

import classes
import defaults


def agent_table(rows):
    """Table for selecting agents"""
    agent_columns = [
        {"headerName": "Name", "field": "agent_name", "sortable": True, "checkboxSelection": True},
        {"headerName": "Identity", "field": "identity"},
        {"headerName": "Configuration", "field": "config"},
    ]

    def update_choice(new_name, new_id, new_config):  # Pass through objects
        """Updates the values for identity and config input based on which agent was picked"""
        new_id.value = defaults.agent_identity_dict[new_name.value]
        new_config.value = str(defaults.agent_config_dict[new_name.value])
        new_id.update()
        new_config.update()

    def updateTable(agent_name: str, config: str):
        for row in table.rows:
            if agent_name == row["agent_name"]:
                row["config"] = config.strip()

                table.selected.clear()
                table.update()

    def edit_config(row):
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Edit Configuration for {row['agent_name']}")

            config = ui.textarea(label="Agent Configuration", value=row["config"]).style("width: 500px")
            ui.button("Save Configuration of Agent", on_click=lambda: (updateTable(row["agent_name"], config.value), dialog.close()))

        dialog.open()

    with ui.table(title="Agents", columns=agent_columns, rows=rows, row_key="agent_name", selection="multiple").classes("w-75") as table:
        with table.add_slot("header"):
            with table.row():
                with table.cell():
                    ui.button(on_click=lambda: (
                        table.add_rows({"agent_name": new_name.value, "identity": new_id.value, "config": new_config.value,}),
                        new_name.set_value(list(defaults.AgentName)[0].value),
                        new_id.set_value(list(defaults.AgentIdentity)[0].value),
                        new_config.set_value(defaults.agent_config_dict[new_name.value]),
                        table.update()
                    ), icon="add").props("flat fab-mini")

                with table.cell():
                    new_name = ui.select(defaults.agent_name_list, value=defaults.agent_name_list[0], on_change=lambda: update_choice(new_name, new_id, new_config))
                with table.cell():
                    new_id = ui.input(label="Identity", value=defaults.agent_identity_dict[new_name.value])
                with table.cell():
                    new_config = ui.textarea(label="Configuration", value=defaults.agent_config_dict[new_name.value].strip())

    with ui.row():
        ui.button("Edit", on_click=lambda: edit_config(*table.selected)).bind_visibility_from(table, "selected", backward=lambda val: bool(val))
        ui.button("Remove",on_click=lambda: (table.remove_rows(*table.selected), table.selected.clear())).bind_visibility_from(table, "selected", backward=lambda val: bool(val))

    return table

def platform_table(rows: List[dict]):
    """Table to display installed machines/instances"""

    platform_columns = [
        {"headerName": "Machine", "field": "machine_name", "sortable": True, "checkboxSelection": True},
        {"headerName": "Instances", "field": "instances"},
        {"headerName": "Status", "field": "status"},
    ]

    async def open_confirm_page():
        """Creates endpoint required for confirm page and opens confirm page"""

        row = await grid.get_selected_row()
        if row:
            machine_name = row["machine_name"]
            ui.open(f"http://127.0.0.1:8080/confirm/{machine_name}")
        else:
            ui.notify("A Machine was not Selected")

    grid = ui.aggrid(
        {
            "defaultColDef": {"flex": 1},
            "columnDefs": platform_columns,
            "rowData": rows,
            "rowSelection": "single",
        },
        html_columns=[1]).classes("max-h-40")

    ui.button("Deploy Machine", on_click=open_confirm_page)

    return grid


def machine_table(rows):
    """Table to display existing machines; Allows for removal of machines"""

    machine_columns = [
        {"name": "name", "label": "Machine Name", "field": "name", "sortable": True},
        {"name": "ip_address", "label": "IP Address", "field": "ip_address", "sortable": True}
        # {'name': 'date_created', 'label': 'Date Created', 'field': 'date_created'}
    ]

    def remove_machine(machine: str):
        """Remove machine from inventory"""
        machine_str = machine.replace("'", '"')
        machine_list = json.loads(machine_str)
        machine_name = machine_list[0]["name"]
        machine_ip = machine_list[0]["ip_address"]

        with open(os.path.expanduser("~/.volttron_installer/platforms/machines.yml"), "r") as machines_file:
            machines_dict = safe_load(machines_file.read())

        for instance_dir in os.listdir(os.path.expanduser("~/.volttron_installer/platforms")):
            if os.path.isdir(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_dir}")):
                with open(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_dir}/{instance_dir}.yml"), "r") as instance_file:
                    instance_dict = safe_load(instance_file.read())

                    if "vip_address" in instance_dict["config"]:
                        parsed_url = urlparse(instance_dict["config"]["vip_address"])

                        ip = parsed_url.hostname

                        if ip == machine_ip:
                            del instance_dict["config"]["vip_address"]

                with open(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_dir}/{instance_dir}.yml"), "w") as instance_file:
                    dump(instance_dict, instance_file)

        del machines_dict["machines"][f"{machine_name}"]

        with open(os.path.expanduser("~/.volttron_installer/platforms/machines.yml"), "w") as machines_file:
            dump(machines_dict, machines_file)

        table.remove_rows(*table.selected)
        table.selected.clear()

    def add_machine(name: str, ip: str):
        """Add machine to inventory"""
        if os.path.exists(os.path.expanduser("~") + "/.volttron_installer/platforms/machines.yml"):
            with open(os.path.expanduser("~") + "/.volttron_installer/platforms/machines.yml", "r") as machines_file:
                machines_dict = safe_load(machines_file.read())

            machines_dict["machines"].update({name: {"ip": ip}})

            with open(os.path.expanduser("~") + "/.volttron_installer/platforms/machines.yml", "w") as machines_file:
                dump(machines_dict, machines_file)
        else:
            with open(os.path.expanduser("~") + "/.volttron_installer/platforms/machines.yml", "w") as machines_file:
                machines_dict = {"machines": {name: {"ip": ip}}}

                dump(machines_dict, machines_file)

    table = ui.table(title="Host Machines", columns=machine_columns, rows=rows, row_key="name", selection="single").classes("w-75")

    with table.add_slot("header"):
        with table.row():
            with table.cell():
                ui.button(
                    on_click=lambda: (
                        table.add_rows({"name": str(new_name.value), "ip_address": new_ip.value}),
                        add_machine(new_name.value, new_ip.value),
                        new_name.set_value(""),
                        new_ip.set_value(""),
                        table.update()
                        ), icon="add").props("flat fab-mini")
            with table.cell():
                new_name = ui.input(label="Machine Name")
            with table.cell():
                new_ip = ui.input(label="IP Address")

    with ui.row().bind_visibility_from(table, "selected", backward=lambda val: bool(val)):
        ui.button("Remove", on_click=lambda: remove_machine(label.text))

    with ui.row():
        ui.label("Current Selection:")
        label = ui.label().bind_text_from(table, "selected", lambda val: str(val))

    return table

def instance_table(rows):
    instance_columns = [
        {"name": "name", "label": "Instance Name", "field": "name", "sortable": True},
        # {'name': 'date_created', 'label': 'Date Created', 'field': 'date_created'}
    ]

    def open_instance_page(instance: str):
        """Creates endpoint required for instance edit page and opens the instance edit page"""
        instance_str = instance.replace("'", '"')
        instance_list = json.loads(instance_str)
        original_instance_name = instance_list[0]["name"]

        ui.open(f"http://127.0.0.1:8080/edit/{original_instance_name}")

    def add_instance(instance_name: str):
        instance = classes.Instance(name=instance_name, message_bus="", vip_address="", agents=[])
        instance.write_platform_config()

    def remove_instance(instance: str):
        """Removes all files related to instance and removes instance from inventory"""
        instance_str = instance.replace("'", '"')
        instance_list = json.loads(instance_str)
        instance_name = instance_list[0]["name"]

        with open(os.path.expanduser("~") + "/.volttron_installer/platforms/inventory.yml", "r") as inventory_file:
            inventory_dict = safe_load(inventory_file.read())

            del inventory_dict["all"]["hosts"][f"{instance_name}"]

        with open(os.path.expanduser("~") + "/.volttron_installer/platforms/inventory.yml", "w") as inventory_file:
            dump(inventory_dict, inventory_file)

        rmtree(os.path.expanduser("~") + f"/.volttron_installer/platforms/{instance_name}")

        table.remove_rows(*table.selected)
        table.selected.clear()

    with ui.table(title="Instances", columns=instance_columns, rows=rows, row_key="name", selection="single").classes("w-75") as table:
        with table.add_slot("header"):
            with table.row():
                with table.cell():
                    ui.button(
                        on_click=lambda: (
                            table.add_rows({"name": str(new_name.value)}),
                            add_instance(new_name.value),
                            new_name.set_value(""),
                            table.update(),
                        ), icon="add").props("flat fab-mini")
                with table.cell():
                    new_name = ui.input(label="Instance Name")

    with ui.row().bind_visibility_from(table, "selected", backward=lambda val: bool(val)):
        ui.button("Edit", on_click=lambda: open_instance_page(label.text))
        ui.button("Remove", on_click=lambda: remove_instance(label.text))

    with ui.row():
        ui.label("Current Selection:")
        label = ui.label().bind_text_from(table, "selected", lambda val: str(val))

    return table