from nicegui import ui
from shutil import rmtree
from typing import List
from urllib.parse import urlparse
from yaml import safe_load

from new_volttron_installer import defaults
from new_volttron_installer.classes import Agent, Instance

import json
import os

def load_info(instance_name):
    ''' Loads info about machine for the selected instance for correct display'''
    
    agent_rows = []
    machine_list = []
    ip_list = []

    # Get machine info about instance for correct data display
    if os.path.exists(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_name}")):
        with open(os.path.expanduser(f"~/.volttron_installer/platforms/{instance_name}/{instance_name}.yml"), "r") as instance_config:
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
    
    return machine_list, ip_list, ip_address, port_num, agent_rows

def save_instance(old_instance_name: str, new_instance_name: str, selected_machine: str, checkbox: bool, port: int, machine_list: list, ip_list: list, more_config: str, table_rows: List[dict]):
    """Saves instance that user created/edited"""
    instance = Instance(name="", message_bus="", vip_address="", agents=[])

    agent_list = []
    for agent in table_rows:
        for num in range(0, 16):
            if list(defaults.AgentName)[num].value in agent["agent_name"]:
                agent["source"] = list(defaults.AgentSource)[num].value

                picked_agent = Agent(name=agent["agent_name"], identity=agent["identity"], source=agent["source"], config=agent["config"])

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

    ui.open("http://127.0.0.1:8080/instances")

def agent_table(rows):
    """Table for selecting agents"""
    agent_columns = [
        {"name": "name", "label": "Name", "field": "agent_name", "sortable": True, "checkboxSelection": True},
        {"name": "identity", "label": "Identity", "field": "identity"},
        {"name": "config", "label": "Configuration", "field": "config"},
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

    with ui.table(title="Agents", columns=agent_columns, rows=rows, row_key="agent_name", selection="single").classes("w-75") as table:
        with table.add_slot("top-left"):
            with table.row().style("display: inline-block"):
                with table.cell():
                    new_name = ui.select(defaults.agent_name_list, value=defaults.agent_name_list[0], on_change=lambda: update_choice(new_name, new_id, new_config))
                with table.cell().style("padding-top: 50px"):
                    new_id = ui.input(label="Agent Identity", value=defaults.agent_identity_dict[new_name.value])
                with table.cell():
                    new_config = ui.textarea(label="Configuration", value=defaults.agent_config_dict[new_name.value].strip()).classes("w-64")
                with table.cell().style("margin-left: 20px"):
                    ui.button(on_click=lambda: (
                        table.add_rows({"agent_name": new_name.value, "identity": new_id.value, "config": new_config.value,}),
                        new_name.set_value(list(defaults.AgentName)[0].value),
                        new_id.set_value(list(defaults.AgentIdentity)[0].value),
                        new_config.set_value(defaults.agent_config_dict[new_name.value]),
                        table.update()), 
                        icon="add").props("flat fab-mini")

    with ui.row():
        ui.button("Edit", on_click=lambda: edit_config(*table.selected)).bind_visibility_from(table, "selected", backward=lambda val: bool(val))
        ui.button("Remove",on_click=lambda: (table.remove_rows(*table.selected), table.selected.clear())).bind_visibility_from(table, "selected", backward=lambda val: bool(val))

    return table

@ui.page("/edit/{instance_name}")
def show_edit_instance(instance_name: str):
    """Page where users can edit instance that the user picked"""
    
    machine_list, ip_list, ip_address, port_num, agent_rows = load_info(instance_name)

    ui.label(f"Configuration of {instance_name}").style("font-size: 26px")
    ui.label("Enter the name of your instance")
    
    new_instance_name = ui.input(
        label="Instance Name",
        value=instance_name,
        validation={"Please enter a Instance Name": lambda value: value.strip()})
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
    
    ui.label("Pick your agent and overwrite the default configuration/identity if needed. Click the 'Configuration' button to create specific configurations for an agent.")

    table = agent_table(agent_rows)
    ui.button("Configuration", on_click=lambda: ui.open("http://127.0.0.1:8080/config"))

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
            table.rows
        )
    )