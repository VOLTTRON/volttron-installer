import reflex as rx
from typing import Literal

class ConfigStoreEntryModelView(rx.Base):
    path: str = ""
    data_type: Literal["CSV", "JSON"] = "JSON"
    value: str = ""

    contains_errors: bool = False
    safe_entry: dict[str, str] = {}
    component_id: str = "_"

    csv_variants: dict[str, dict[str, list[str]]] = {
        "Default 1" : {
            "Reference Point Name": ["default 1"]*10,
            "Volttron Point Name": [""]*10,
            "Units": [""]*10,
            "Units Details": [""]*10,
            "Modbus Register": [""]*10,
            "Writable": [""]*10,
            "Point Address": [""]*10,
            "Default Value": [""]*10,
            "Notes": [""]*10,
        },
        "Default 2": {
            "Point Name": [""]*10,
            "Volttron Point Name": [""]*10,
            "Units": [""]*10,
            "Unit Details": [""]*10,
            "BACnet Object Type": [""]*10,
            "Property": [""]*10,
            "Writable": ["f"]*10,
            "Index": [""]*10,
            "Notes" : [""]*10,
        }
    }

    def dict(self, *args, **kwargs) -> dict:
        return {
            "path": self.path,
            "data_type": self.data_type,
            "value": self.value,
            "component_id": self.component_id
        }

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "data_type": self.data_type,
            "value": self.value,
            "component_id": self.component_id
        }

class AgentModelView(rx.Base):
    identity: str = ""
    source: str = ""
    config: str = ""
    config_store: list[ConfigStoreEntryModelView] = []
    # config_store: dict[str, ConfigStoreEntryModelView] = {}

    contains_errors: bool = False
    uncaught: bool = True
    safe_agent: dict[str, str] = {}

    routing_id: str = ""


class HostEntryModelView(rx.Base):
    id: str = ""
    ansible_user: str = ""
    ansible_host: str = ""
    ansible_port: int = 22
    ansible_connection: Literal["ssh", "local"] = "ssh"
    http_proxy: str = ""
    https_proxy: str = ""
    volttron_venv: str = ""
    volttron_home: str = "~/.volttron"
    host_configs_dir: str | None = None

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "ansible_user": self.ansible_user,
            "ansible_host": self.ansible_host,
            "ansible_port": int(self.ansible_port),
            "ansible_connection": self.ansible_connection,
            "http_proxy": "" if self.http_proxy is None else self.http_proxy,
            "https_proxy": "" if self.https_proxy is None else self.https_proxy,
            "volttron_venv": "" if self.volttron_venv is None else self.volttron_venv,
            "volttron_home": self.volttron_home,
            "host_configs_dir": "" if self.host_configs_dir is None else self.host_configs_dir
        }

class PlatformConfigModelView(rx.Base):
    instance_name: str = "volttron1"
    vip_address: str = "tcp://127.0.0.1:22916"
    message_bus: Literal["zmq"] = "zmq"
    # options: list[KeyValuePair] = []

    def to_dict(self) -> dict[str, str]:
        return {
            "instance_name" : self.instance_name,
            "vip_address" : self.vip_address,
            "message_bus" : self.message_bus,
            "options" : []
        }

class PlatformModelView(rx.Base):
    config: PlatformConfigModelView = PlatformConfigModelView()
    agents: dict[str, AgentModelView] = {}