from nicegui import ui
from typing import List
from urllib import urlparse
from yaml import safe_load

from ..pages import Pages, show_global_header
from ..classes import Instance, Inventory
import os

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
            if row["instances"] == "None":
                ui.notify("Please assign an instance to the machine before deploying.")
            else:
                machine_name = row["machine_name"]
                ui.open(f"http://127.0.0.1:8080/confirm/{machine_name}")
        else:
            ui.notify("A Machine was not Selected.")

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

def default_home_page():
    """Default home page; called when no instances/machines exist"""
    show_global_header(Pages.HOME)

    with ui.row():
        ui.label("There are no host machines added or instances installed.")
        ui.button("Add a Host Machine", on_click=lambda: ui.open("http://127.0.0.1:8080/machines"))

def home_page():
    """Home Page; called when instances/machines do exist"""
    show_global_header(Pages.HOME)

    platform_rows = []
    machine_list = []
    ip_list = []

    # Create and append table rows from inventory and platform config files
    platforms_path = os.path.expanduser("~") + "/.volttron_installer/platforms/"
    if os.path.exists(os.path.expanduser("~/.volttron_installer/platforms/inventory.yml")):
        inventory = Inventory.read_inventory("inventory")

    with open(os.path.expanduser("~/.volttron_installer/platforms/machines.yml"), "r") as machines_config:
        machines_dict = safe_load(machines_config.read())

        for machine, ip in machines_dict["machines"].items():
            machine_list.append(machine)
            ip_list.append(ip["ip"])

    for index, machine in enumerate(machine_list):
        instance_list = []

        if os.path.exists(os.path.expanduser("~/.volttron_installer/platforms/inventory.yml")):
            for instance in inventory.hosts:
                if os.path.isdir(platforms_path + instance):
                    instance_obj = Instance.read_platform_config(instance)

                    parsed_url = urlparse(instance_obj.vip_address)
                    ip_address = parsed_url.hostname

                    if ip_address == ip_list[index] or ip_address == "0.0.0.0":
                        instance_list.append(instance_obj.name)
                        
            if instance_list == []:
                platform_rows.append({"machine_name": machine, "instances": "None", "status": ""})
            else:
                link_str = ""
                for index, instance in enumerate(instance_list):
                    if index == len(instance_list) - 1:
                        link_str += (f'<a href="http://127.0.0.1:8080/edit/{instance}">{instance}</a>')
                    else:
                        link_str += (f'<a href="http://127.0.0.1:8080/edit/{instance}">{instance}</a>, ')

                platform_rows.append({"machine_name": machine, "instances": link_str, "status": ""})
        else:
            platform_rows.append({"machine_name": machine, "instances": "None", "status": ""})

    with ui.row():
        ui.label("Deploy a machine by selecting one below or Add a Machine/Instance")

    with ui.row():
        ui.button("Add Machine", on_click=lambda: ui.open("http://127.0.0.1:8080/machines")).tooltip("A device with an IP address that an instance can bind to.")
        ui.button("Add Instance", on_click=lambda: ui.open("http://127.0.0.1:8080/instances")).tooltip("A VOLTTRON instance that allows for configuration.")

    table = platform_table(platform_rows)

@ui.page("/")
def show_home():
        """Checks for existing existing instances/machines and redirects to appropriate home page"""

        # Check if base directories exist; Redirect to appropriate home page
        if os.path.exists(os.path.expanduser("~/.volttron_installer/platforms")):
            if os.path.exists(os.path.expanduser("~/.volttron_installer/platforms/machines.yml")):
                home_page()
            else:
                default_home_page()
        else:
            os.makedirs(os.path.expanduser("~/.volttron_installer"), exist_ok=True)
            os.makedirs(os.path.expanduser("~/.volttron_installer/platforms"), exist_ok=True)
            default_home_page()