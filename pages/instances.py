from nicegui import ui
from shutil import rmtree
from yaml import dump, safe_load

from new_volttron_installer.pages import Pages, show_global_header
from new_volttron_installer.classes import Instance, Inventory

import json
import os

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

    def add_instance(instance_name: str, table):
        if instance_name.strip() in {"", None}:
            ui.notify("Please enter a name for the instance.")
        else:
            instance = Instance(name=instance_name, message_bus="", vip_address="", agents=[])
            instance.write_platform_config()

            instance_list = []

            for instance_dir in os.listdir(os.path.expanduser("~/.volttron_installer/platforms")):
                if os.path.isdir(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_dir}")):
                    instance_list.append(str(instance_dir))
        
            instance_list.sort()
        
            inventory = Inventory(hosts=instance_list)
            inventory.write_inventory("inventory")

            ui.notify(f"Opening Configuration for {instance_name}.")
            open_instance_page(instance_name)

            table.add_rows({"name": str(instance_name.value)})
            table.update()

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

    with ui.table(columns=instance_columns, rows=rows, row_key="name", selection="single").classes("w-75") as table:
        with table.add_slot("top-left"):
            with table.row():
                with table.cell():
                    new_name = ui.input(label="Instance Name", value="")
                with table.cell():
                    ui.button(
                        on_click=lambda: (
                            add_instance(new_name.value, table),
                            new_name.set_value("")), 
                            icon="add").props("flat fab-mini")

    with ui.row().bind_visibility_from(table, "selected", backward=lambda val: bool(val)):
        ui.button("Edit", on_click=lambda: open_instance_page(label.text))
        ui.button("Remove", on_click=lambda: remove_instance(label.text))

    with ui.row():
        ui.label("Current Selection:").bind_visibility_from(table, 'selected', backward=lambda val: bool(val))
        label = ui.label().bind_text_from(table, "selected", lambda val: str(val)).bind_visibility_from(table, 'selected', backward=lambda val: bool(val))

    return table

@ui.page("/instances")
def show_instances():
    """Page for instance display"""

    rows = []
    # Create rows for instance table
    if os.path.exists(os.path.expanduser("~/.volttron_installer/platforms/inventory.yml")):
        inventory = Inventory.read_inventory("inventory")
        for instance in inventory.hosts:
            rows.append({"name": str(instance)})

    show_global_header(Pages.INSTANCES)

    ui.label("Add an instance by entering its name and edit an instance through the table")
    table = instance_table(rows)