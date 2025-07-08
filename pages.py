from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager, Queue
from nicegui import app, ui
from shutil import rmtree
from typing import List
from urllib.parse import urlparse
from yaml import safe_load

import asyncio
import json
import os

import classes
import defaults
import header
import install
import tables

pool = ProcessPoolExecutor()

def save_instance(old_instance_name: str, new_instance_name: str, selected_machine: str, checkbox: bool, port: int, machine_list: list, ip_list: list, more_config: str, table_rows: List[dict]):
    """Saves instance that user created/edited"""
    instance = classes.Instance(name="", message_bus="", vip_address="", agents=[])

    agent_list = []
    for agent in table_rows:
        for num in range(0, 16):
            if list(defaults.AgentName)[num].value in agent["agent_name"]:
                agent["source"] = list(defaults.AgentSource)[num].value

                picked_agent = classes.Agent(name=agent["agent_name"], identity=agent["identity"], source=agent["source"], config=agent["config"])

        agent_list.append(picked_agent)

    if checkbox == False:
        for index, machine in enumerate(machine_list):
            if machine == selected_machine:
                ip_address = ip_list[index]
                instance.vip_address = f"tcp://{ip_address}:{port}"
    else:
        ip_address = "0.0.0.0"
        instance.vip_address = f"tcp://{ip_address}:{port}"

    instance.name = new_instance_name
    instance.agents = agent_list

    lines = more_config.split("\n")
    for line in lines:
        if "message-bus" in line:
            instance.message_bus = line.split("=")[1].strip()
        elif "web-ssl-cert" in line:
            instance.web_ssl_cert = line.split("=")[1].strip()
        elif "web-ssl-key" in line:
            instance.web_ssl_key = line.split("=")[1].strip()
        elif "volttron-central-address" in line:
            instance.volttron_central_address = line.split("=")[1].strip()
        elif "bind-web-address" in line:
            instance.bind_web_address = line.split("=")[1].strip()

    if new_instance_name != old_instance_name:
        rmtree(os.path.expanduser(f"~/.volttron_installer/platforms/{old_instance_name}"))

    instance.write_platform_config()

    instance_list = []

    for instance_dir in os.listdir(os.path.expanduser("~/.volttron_installer/platforms")):
        if os.path.isdir(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_dir}")):
            instance_list.append(str(instance_dir))

    instance_list.sort()

    inventory = classes.Inventory(hosts=instance_list)
    inventory.write_inventory("inventory")

    ui.open("http://127.0.0.1:8080/instances")

def default_home_page():
    """Default home page; called when no instances/machines exist"""
    header.add_header("Home")

    with ui.row():
        ui.label("There are no host machines added or instances installed.")
        ui.button("Add a Host Machine", on_click=lambda: ui.open("http://127.0.0.1:8080/machines"),)

def home_page():
    """Home Page; called when instances/machines do exist"""
    header.add_header("Home")

    platform_rows = []
    machine_list = []
    ip_list = []

    # Create and append table rows from inventory and platform config files
    platforms_path = os.path.expanduser("~") + "/.volttron_installer/platforms/"
    inventory = classes.Inventory.read_inventory("inventory")

    with open(os.path.expanduser("~/.volttron_installer/platforms/machines.yml"), "r") as machines_config:
        machines_dict = safe_load(machines_config.read())

        for machine, ip in machines_dict["machines"].items():
            machine_list.append(machine)
            ip_list.append(ip["ip"])

    for index, machine in enumerate(machine_list):
        instance_list = []

        link_str = ""
        for instance in inventory.hosts:
            if os.path.isdir(platforms_path + instance):
                instance_obj = classes.Instance.read_platform_config(instance)

                parsed_url = urlparse(instance_obj.vip_address)
                ip_address = parsed_url.hostname

                if ip_address == ip_list[index] or ip_address == "0.0.0.0":
                    instance_list.append(instance_obj.name)

        for index, instance in enumerate(instance_list):
            if index == len(instance_list) - 1:
                link_str += (f'<a href="http://127.0.0.1:8080/edit/{instance}">{instance}</a>')
            else:
                link_str += (f'<a href="http://127.0.0.1:8080/edit/{instance}">{instance}</a>, ')

        platform_rows.append({"machine_name": machine, "instances": link_str, "status": ""})

    with ui.row():
        ui.label("Deploy a machine by selecting one below or Add a Machine/Instance")

    with ui.row():
        ui.button("Add Machine", on_click=lambda: ui.open("http://127.0.0.1:8080/machines")).tooltip("A device with an IP address that an instance can bind to.")
        ui.button("Add Instance", on_click=lambda: ui.open("http://127.0.0.1:8080/instances")).tooltip("A VOLTTRON instance that allows for configuration.")

    table = tables.platform_table(platform_rows)

def confirm_platform(machine_name: str):
    """Page that will show selected machine/instances; can be either one machine or all machines. Can be submitted for installation of those instances"""

    agent_columns = [
        {"name": "agent_name", "label": "Name", "field": "name"},
        {"name": "identity", "label": "Identity", "field": "identity"},
        {"name": "config", "label": "Configuration", "field": "config"},
    ]
    instance_list = []

    with open(os.path.expanduser("~/.volttron_installer/platforms/machines.yml"), "r") as machines_file:
        machines_dict = safe_load(machines_file.read())

    for instance_dir in os.listdir(os.path.expanduser("~/.volttron_installer/platforms")):
        if os.path.isdir(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_dir}")):
            with open(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_dir}/{instance_dir}.yml"), "r") as instance_file:
                instance_dict = safe_load(instance_file.read())

                if "vip-address" in instance_dict["config"]:
                    parsed_url = urlparse(instance_dict["config"]["vip-address"])
                    ip = parsed_url.hostname

                    if ip == machines_dict["machines"][f"{machine_name}"]["ip"]:
                        instance = classes.Instance.read_platform_config(instance_dir)
                        instance_list.append(instance)
                    elif ip == "0.0.0.0.":
                        instance = classes.Instance.read_platform_config(instance_dir)
                        instance_list.append(instance)

    async def start_installation():
        """Async event handler; Will install platform"""
        progress.visible = True
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(pool, install.install_platform, queue, instance_list, password.value)
        ui.open("http://127.0.0.1:8080/")

    queue = Manager().Queue()

    header.add_header("Confirm")
    ui.label("Overview of Configuration").style("font-size: 26px")

    with ui.row():
        ui.label("Machine Name:")
        ui.label(machine_name)

    with ui.row():
        ui.label("IP Address:")
        ui.label(machines_dict["machines"][f"{machine_name}"]["ip"])
    ui.separator()

    ui.label("Instances").style("font-size: 20px;")
    for instance in instance_list:
        rows = []

        for agent in instance.agents:
            rows.append({"name": agent.name, "identity": agent.identity, "config": str(agent.config)})

        with ui.row():
            ui.label("Instance Name:")
            ui.label(instance.name)

        with ui.row():
            ui.label("VIP Address:")
            ui.label(instance.vip_address)
        ui.separator()

        more_config = ""
        ui.label("Extra Configuration").style("font-size: 20px")
        with ui.column():
            with ui.row():
                ui.label("Message Bus:")
                ui.label(instance.message_bus)

            if instance.bind_web_address:
                with ui.row():
                    ui.label("Bind Web Address:")
                    ui.label(instance.bind_web_address)

            if instance.volttron_central_address:
                with ui.row():
                    ui.label("Volttron Central Address:")
                    ui.label(instance.volttron_central_address)

            if instance.web_ssl_cert:
                with ui.row():
                    ui.label("Web SSL Certificate:")
                    ui.label(instance.web_ssl_cert)

            if instance.web_ssl_key:
                with ui.row():
                    ui.label("Web SSL Key:")
                    ui.label(instance.web_ssl_key)
        ui.separator()

        with ui.row():
            ui.table(title="Agents", columns=agent_columns, rows=rows)
        ui.separator()

    ui.label("Enter your password then click 'Confirm' to start the installation process")
    with ui.row():
        password = ui.input(
            placeholder="Password",
            label="Password",
            password=True,
            password_toggle_button=True,
            validation={"Please enter your password": lambda value: value.strip()},
        )

        ui.button("Cancel", on_click=lambda: ui.open("http://127.0.0.1:8080/"))
        ui.button("Confirm", on_click=start_installation)

        progress = ui.circular_progress(min=0, max=100, value=0, size="xl").props("instant-feedback")
        progress.visible = False

    ui.timer(0.1, callback=lambda: progress.set_value(queue.get() if not queue.empty() else progress.value))
def main():
    @ui.page("/")
    def index():
        """Checks for existing existing instances/machines and redirects to appropriate home page"""

        # Check if any directories exist
        if os.path.exists(os.path.expanduser("~/.volttron_installer/platforms")):
            if os.listdir(os.path.expanduser("~/.volttron_installer/platforms")):
                home_page()
            else:
                default_home_page()
        else:
            os.makedirs(os.path.expanduser("~/.volttron_installer"))
            os.makedirs(os.path.expanduser("~/.volttron_installer/platforms"))
            default_home_page()

    @ui.page("/machines")
    def machines():
        """Page for adding and removing machines"""

        rows = []
        if os.path.exists(os.path.expanduser("~/.volttron_installer/platforms/machines.yml")):
            with open(os.path.expanduser("~/.volttron_installer/platforms/machines.yml"), "r") as machines_file:
                machines_dict = safe_load(machines_file.read())

                for machine, ip in machines_dict["machines"].items():
                    rows.append({"name": str(machine), "ip_address": str(ip["ip"])})

        header.add_header("Machines")

        ui.label("Enter your machine name and ip address and add them to the table")
        table = tables.machine_table(rows)

    @ui.page("/instances")
    def instances():
        """Page for instance display"""

        rows = []
        # Create rows for instance table
        if os.path.exists(
            os.path.expanduser("~/.volttron_installer/platforms/inventory.yml")):
            inventory = classes.Inventory.read_inventory("inventory")

            for instance in inventory.hosts:
                rows.append({"name": str(instance)})

        header.add_header("Instances")

        ui.label("Add an instance by entering its name and edit an instance through the table")

        table = tables.instance_table(rows)

    @ui.page("/edit/{instance_name}")
    def edit_instance(instance_name: str):
        """Page where users can edit instance that the user picked"""

        agent_rows = []
        machine_list = []
        ip_list = []

        # Get machine info about instance for correct data display
        if os.path.exists(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_name}")):
            with open(
                os.path.expanduser(f"~/.volttron_installer/platforms/{instance_name}/{instance_name}.yml"), "r") as instance_config:
                instance_dict = safe_load(instance_config.read())

            for agent, config in instance_dict["agents"].items():
                with open(config["agent_config"], "r") as config_file:
                    config = safe_load(config_file.read())

                for num in range(0, 16):
                    if agent == list(defaults.AgentIdentity)[num].value:
                        agent_name = list(defaults.AgentName)[num].value

                config = (str(config).replace("'", '"').replace("False", "false").replace("True", "true").replace("None", "null"))  # Change single quotes to double so str can be converted to dict
                config_obj = json.loads(str(config))
                config_str = json.dumps(config_obj, indent=2)
                agent_rows.append({"agent_name": agent_name, "identity": agent, "config": config_str})

            if "vip-address" in instance_dict["config"]:
                vip_address = instance_dict["config"]["vip-address"]
                parsed_url = urlparse(vip_address)
                ip_address = parsed_url.hostname
                port_num = parsed_url.port
            else:
                ip_address = None
                port_num = None
        else:
            agent_rows = []
            ip_address = None

        with open(os.path.expanduser("~/.volttron_installer/platforms/machines.yml"), "r") as machines_config:
            machines_dict = safe_load(machines_config.read())

            for machine, ip in machines_dict["machines"].items():
                machine_list.append(machine)
                ip_list.append(ip["ip"])

        ui.label(f"Configuration of {instance_name}").style("font-size: 26px")

        ui.label("Enter the name of your instance")
        new_instance_name = ui.input(
            label="Instance Name",
            value=instance_name,
            validation={"Please enter a Instance Name": lambda value: value.strip()},
        )
        ui.separator()

        if ip_address is not None:
            for index, ip in enumerate(ip_list):
                if ip == ip_address:
                    machine = machine_list[index]

        ui.label("Pick which machine and port this instance will be hosted on")
        with ui.row():
            if ip_address is None:
                    selected_machine = ui.select(machine_list, value=machine_list[0])
                    port = ui.input("Port #", value="22916")
                    ip_checkbox = ui.checkbox("Bind to all IP's?")
            elif ip_address == "0.0.0.0":
                selected_machine = ui.select(machine_list, value=machine_list[0])
                if port_num is None:
                    port = ui.input("Port #", value="22916")
                else:
                    port = ui.input("Port #", value=port_num)
                ip_checkbox = ui.checkbox("Bind to all IP's?", value=True)
            else:
                selected_machine = ui.select(machine_list, value=machine)
                if port_num is None:
                    port = ui.input("Port #", value="22916")
                else:
                    port = ui.input("Port #", value=port_num)
                ip_checkbox = ui.checkbox("Bind to all IP's?")


        ui.separator()

        with ui.row():
            ui.label("Enter more configuration below")

            with ui.link(target="https://volttron.readthedocs.io/en/main/deploying-volttron/platform-configuration.html#volttron-config-file", new_tab=True):
                with ui.icon("help_outline", color="black").style("text-decoration: none;"):
                    ui.tooltip("Need Help?")

        combine_lines = ""
        with open(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_name}/{instance_name}.yml")) as instance_config:
            instance_dict = safe_load(instance_config.read())

            for key, value in instance_dict["config"].items():
                if "instance-name" in key or "vip-address" in key:
                    pass
                elif "message-bus" in key:
                    if value == "":
                        pass
                    else:
                        line_str = f"{key} = {value}\n"
                        combine_lines += line_str
                else:
                    line_str = f"{key} = {value}\n"
                    combine_lines += line_str

            more_configs = ui.textarea(label="Extra Configuration", placeholder="Start typing...", value=combine_lines).style("width: 600px")
        ui.separator()

        ui.label("Pick your agent and overwrite the default configuration/identity if needed")
        table = tables.agent_table(agent_rows)

        ui.button(
            "Save Changes to Instance", on_click=lambda: save_instance(
                instance_name,
                new_instance_name.value,
                selected_machine.value,
                ip_checkbox.value,
                port.value,
                machine_list,
                ip_list,
                more_configs.value,
                table.rows,
            ),
        )

    @ui.page("/confirm/{machine_name}")
    def confirm(machine_name: str):
        confirm_platform(machine_name)

    app.on_shutdown(pool.shutdown)
    ui.run(title="VOLTTRON")

if __name__ in {"__main__", "__mp_main__"}:
    main()