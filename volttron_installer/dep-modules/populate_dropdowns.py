from flet import Dropdown, dropdown
from volttron_installer.modules.global_configs import global_agents, global_drivers, global_hosts


def numerate_agent_dropdown() -> Dropdown:
    dropdown_options = [dropdown.Option(text=key) for key in global_agents.keys()]
    return Dropdown(options=dropdown_options)

def numerate_host_dropdown() -> Dropdown:
    dropdown_options = [dropdown.Option(text=key) for key in global_hosts.keys()]
    return Dropdown(options=dropdown_options)

def numerate_configs_dropdown() -> Dropdown:
    dropdown_options = [dropdown.Option(text="None")]
    driver_options = [dropdown.Option(text=key) for key in global_drivers.keys()]
    dropdown_options.extend(driver_options)
    return Dropdown(options=dropdown_options)