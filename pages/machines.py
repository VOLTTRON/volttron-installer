from nicegui import ui
from urllib.parse import urlparse
from yaml import dump, safe_load

from new_volttron_installer.pages import Pages, show_global_header

import json
import os

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

    table = ui.table(columns=machine_columns, rows=rows, row_key="name", selection="single").classes("w-75")

    with table.add_slot("top-left"):
        with table.row():
            with table.cell():
                new_name = ui.input(label="Machine Name").classes('w-32')
            with table.cell():
                new_ip = ui.input(label="IP Address")
            with table.cell():
                ui.button(
                    on_click=lambda: (
                        table.add_rows({"name": str(new_name.value), "ip_address": new_ip.value}),
                        add_machine(new_name.value, new_ip.value),
                        new_name.set_value(""),
                        new_ip.set_value(""),
                        table.update()
                        ), icon="add").props("flat fab-mini")

    with ui.row().bind_visibility_from(table, "selected", backward=lambda val: bool(val)):
        ui.button("Remove", on_click=lambda: remove_machine(label.text))

    with ui.row():
        ui.label("Current Selection:")
        label = ui.label().bind_text_from(table, "selected", lambda val: str(val))

    return table

@ui.page("/machines")
def show_machines():
    """Page for adding and removing machines"""
    rows = []
    if os.path.exists(os.path.expanduser("~/.volttron_installer/platforms/machines.yml")):
        with open(os.path.expanduser("~/.volttron_installer/platforms/machines.yml"), "r") as machines_file:
            machines_dict = safe_load(machines_file.read())
            for machine, ip in machines_dict["machines"].items():
                rows.append({"name": str(machine), "ip_address": str(ip["ip"])})
    show_global_header(Pages.MACHINES)
    ui.label("Enter your machine name and ip address and add them to the table")
    table = machine_table(rows)