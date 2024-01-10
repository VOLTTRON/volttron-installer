from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager,  Queue
from nicegui import run, ui
from subprocess import Popen, PIPE
from typing import List
from urllib.parse import urlparse
from yaml import safe_load

import asyncio
import os
import pexpect
import time

from new_volttron_installer.classes import Instance

pool = ProcessPoolExecutor()

def install_platform(q: Queue, instance_list: List[Instance], password: str):
    """Installs platform and updates progress bar as processes are finished"""
    print(instance_list)
    #q.put_nowait(20) # Update progress bar
    
    ## Host Configuration; handles password input; Assumes password was entered correctly
    # host_config_process = pexpect.spawn("ansible-playbook -K -i inventory.yml --connection=local volttron.deployment.host_config")
    # host_config_process.expect("BECOME password: ")
    # host_config_process.sendline(password)

    # host_config_process.expect(pexpect.EOF)
    # print(host_config_process.before.decode())
    #q.put_nowait(40)

    ## Install Platform
    # install_cmd = Popen(['bash', '-c', 'ansible-playbook -i inventory.yml --connection=local volttron.deployment.install_platform'], stdout=PIPE, stderr=PIPE)
    # stdout, stderr = install_cmd.communicate()

    # if stdout is not None:
    #    stdout_str = stdout.decode('utf-8')
    #    print(stdout_str)
    # if stderr is not None:
    #    stderr_str = stderr.decode('utf-8')
    #    print(stderr_str)

    #q.put_nowait(60)

    ## Run Platform
    # run = Popen(['bash', '-c', 'ansible-playbook -i inventory.yml --connection=local volttron.deployment.run_platforms -vvv'])
    # stdout, stderr = run.communicate()
    #
    # if stdout is not None:
    #    stdout_str = stdout.decode("utf-8")
    #    print(stdout_str)
    # if stderr is not None:
    #    stderr_str = stderr.decode("utf-8")
    #    print(stderr_str)

    #q.put_nowait(80)

    ## Configure Agents
    # configure = Popen(['bash', '-c', 'ansible-playbook -i inventory.yml --connection=local volttron.deployment.configure_agents -vvv'])
    # stdout, stderr = configure.communicate()
    #
    # if stdout is not None:
    #    stdout_str = stdout.decode('utf-8')
    #    print(stdout_str)
    # if stderr is not None:
    #    stderr_str = stderr.decode('utf-8')
    #    print(stderr_str)
    q.put_nowait(100)
    print("Installation Finished")
    return "Installation Finished"

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
                        instance = Instance.read_platform_config(instance_dir)
                        instance_list.append(instance)
                    elif ip == "0.0.0.0.":
                        instance = Instance.read_platform_config(instance_dir)
                        instance_list.append(instance)

    async def start_installation():
        """Async event handler; Will install platform"""
        progress.visible = True
        result = await run.cpu_bound(install_platform, queue, instance_list, password.value)
        ui.notify(result)
        ui.open("http://127.0.0.1:8080/")

    queue = Manager().Queue()

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

        ui.timer(0.01, callback=lambda: progress.set_value(queue.get() if not queue.empty() else progress.value))

        ui.button("Cancel", on_click=lambda: ui.open("http://127.0.0.1:8080/"))
        ui.button("Confirm", on_click=start_installation)

        progress = ui.circular_progress(min=0, max=100, value=0, size="xl").props("instant-feedback show-value")
        progress.visible = False

@ui.page("/confirm/{machine_name}")
def show_deploy_page(machine_name: str):
    confirm_platform(machine_name)