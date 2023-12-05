from typing import Optional, List
from dataclasses import dataclass, field
from yaml import dump, safe_load

import json
import os

import defaults

@dataclass
class Agent:
    """Class for Agents"""
    name: str
    identity: str
    source: str
    config: str

@dataclass
class Instance:
    """Class for an Instance"""
    name: str
    message_bus: str
    vip_address: str = "tcp://127.0.0.1:22916"
    bind_web_address: Optional[str] = None
    volttron_central_address: Optional[str] = None
    web_ssl_cert: Optional[str] = None
    web_ssl_key: Optional[str] = None
    agents: List[Agent] = field(default_factory=[])

    def write_platform_config(self):
        """Write Platform Config File"""
        platform_dict = {
            "config": {
                "vip-address": self.vip_address,
                "message-bus": self.message_bus,
            },
            "agents": {},
        }

        if self.bind_web_address is not None:
            platform_dict["config"].update({"bind-web-address": self.bind_web_address})
        if self.volttron_central_address is not None:
            platform_dict["config"].update(
                {"volttron-central-address": self.volttron_central_address}
            )
        if self.web_ssl_cert is not None:
            platform_dict["config"].update({"web-ssl-cert": self.web_ssl_cert})
        if self.web_ssl_key is not None:
            platform_dict["config"].update({"web-ssl-key": self.web_ssl_key})

        os.makedirs(os.path.expanduser("~") + f"/.volttron_installer/platforms/{self.name}", exist_ok=True)
        os.makedirs(os.path.expanduser("~") + f"/.volttron_installer/platforms/{self.name}/agent_configs", exist_ok=True)

        for agent in self.agents:
            for num in range(0, 16):
                if list(defaults.AgentName)[num].value == agent.name:
                    config_str = str(agent.config)
                    config = (config_str.replace("'", '"').replace("False", "false").replace("True", "true").replace("None", "null"))  # Change single quotes to double so str can be converted to dict

                    # Create agent config files
                    id = agent.identity.replace(".", "_")
                    with open(os.path.expanduser(f"~/.volttron_installer/platforms/{self.name}/agent_configs/{id}_config"), "w") as agent_config:
                        agent_config.write(config)

                    agent_config_path = (
                        os.path.expanduser("~")
                        + f"/.volttron_installer/platforms/{self.name}/agent_configs/{id}_config"
                    )
                    agent.config = agent_config_path
                num += 1

            platform_dict["agents"].update(
                {
                    agent.identity: {
                        "agent_source": agent.source,
                        "agent_config": agent.config,
                        "agent_running": True,
                        "agent_enabled": True,
                    }
                }
            )

        with open(os.path.expanduser(f"~/.volttron_installer/platforms/{self.name}/{self.name}.yml"), "w") as platform_config_file:
            dump(platform_dict, platform_config_file)

    @staticmethod
    def read_platform_config(instance: str) -> "Instance":
        """Read Saved Platform Config File"""
        machine_list = []
        ip_list = []
        instance_obj = Instance(name=instance, message_bus="", vip_address="", agents=[])

        with open(os.path.expanduser("~/.volttron_installer/platforms/machines.yml"), "r") as machines_config:
            machines_dict = safe_load(machines_config.read())

            for machine, ip in machines_dict["machines"].items():
                machine_list.append(machine)
                ip_list.append(ip["ip"])

        agent_list = []
        with open(os.path.expanduser(f"~/.volttron_installer/platforms/{instance}/{instance}.yml"), "r") as platform_config_file:
            platform_dict = safe_load(platform_config_file.read())

        # Get variables needed for the platform object; Used for frontend
        instance_obj.vip_address = platform_dict["config"]["vip-address"]
        instance_obj.message_bus = platform_dict["config"]["message-bus"]

        if "bind-web-address" in platform_dict["config"]:
            instance_obj.bind_web_address = platform_dict["config"]["bind-web-address"]
        if "volttron-central-address" in platform_dict["config"]:
            instance_obj.volttron_central_address = platform_dict["config"]["volttron-central-address"]
        if "web-ssl-cert" in platform_dict["config"]:
            instance_obj.web_ssl_cert = platform_dict["config"]["web-ssl-cert"]
        if "web-ssl-key" in platform_dict["config"]:
            instance_obj.web_ssl_key = platform_dict["config"]["web-ssl-key"]

        for agent_identity, config in platform_dict["agents"].items():
            for num in range(0, 16):
                if agent_identity == list(defaults.AgentIdentity)[num].value:
                    agent_name = list(defaults.AgentName)[num].value
                    with open(config["agent_config"], "r") as config_file:
                        data = config_file.read()
                        agent_config = json.loads(data)
                    picked_agent = Agent(
                        name=agent_name,
                        identity=agent_identity,
                        source=config["agent_source"],
                        config=agent_config,
                    )
                    agent_list.append(picked_agent)

        instance_obj.agents = agent_list

        return instance_obj

@dataclass
class Inventory:
    """Class to Create and Read Inventory;"""

    hosts: List[str]

    def write_inventory(self, filename: str):
        """Write Inventory File"""
        count = 0
        inventory_dict = {"all": {"hosts": {}}}

        # Add multiple hosts with their address' to the inventory dictionary;
        for host in self.hosts:
            count += 1
            inventory_dict["all"]["hosts"].update({
                host: {
                    "volttron_home": f"volttron_home{count}"
                }
            })

        with open(os.path.expanduser(f"~/.volttron_installer/platforms/{filename}.yml"), "w") as inventory_file:
            dump(inventory_dict, inventory_file)

    @staticmethod
    def read_inventory(filename: str) -> "Inventory":
        """Read Saved Inventory File"""
        with open(os.path.expanduser(f"~/.volttron_installer/platforms/{filename}.yml"), "r") as inventory_file:
            inventory_dict = safe_load(inventory_file.read())

            hosts = list(inventory_dict["all"]["hosts"].keys())
            inventory_obj = Inventory(hosts=hosts)

            return inventory_obj