import reflex as rx
from typing import Any, Literal

class ConfigStoreEntryModelView(rx.Base):
    path: str = ""
    data_type: Literal["CSV", "JSON"] = "JSON"
    value: str = ""

    contains_errors: bool = False
    safe_entry: dict[str, Any] = {}
    component_id: str = "_"

    uncommitted: bool = True
    changed: bool = False
    valid: bool = False
    in_file: bool = False

    selected_variant: str = "Custom"
    selected_cell: str = ""
    
    csv_variants: dict[str, dict[str, list[str]]] = {
        "Default 1" : {
            "Reference Point Name": [""]*10,
            "Reference Point Name": [""]*10,
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
            "Writable": [""]*10,
            "Writable": [""]*10,
            "Index": [""]*10,
            "Notes" : [""]*10,
        },
        "Custom": {
            "1": [""]*10,
            "2": [""]*10,
            "3": [""]*10,
            "4": [""]*10,
            "5": [""]*10,
            "6": [""]*10,
            "7": [""]*10,
            "8": [""]*10,
            "9" : [""]*10,
        }
    }
    # this field just holds the invalid csv data, so we can have a quick check
    # and stuff like that.
    malformed_csv_data: str = ""

    # these fields are for when we save the config store entry, we can put data into these
    # fields to make it easier to display the data in the agent draft, will also be really
    # easy to make csv_strings out of these fields
    csv_header_row: list[str] = []
    formatted_csv: list[list[str]] = []

    def variant_headers(self) -> list[str]:
        if self.selected_variant in self.csv_variants:
            return list(self.csv_variants[self.selected_variant].keys())
        return []

    def variant_rows(self) -> list[list[str]]:
        working_dict = self.csv_variants[self.selected_variant]
        headers = list(working_dict.keys())
        return [[working_dict[header][i] for header in headers] 
                for i in range(10)]

    def dict(self, *args, **kwargs) -> dict:
        return {
            "path": self.path,
            "data_type": self.data_type,
            "value": str(self.value),
            "component_id": self.component_id,
            "csv_variants": self.csv_variants 
        }

class AgentModelView(rx.Base):
    identity: str = ""
    source: str = ""
    config: str = ""
    config_store: list[ConfigStoreEntryModelView] = []

    contains_errors: bool = False
    is_new: bool = False
    safe_agent: dict[str, Any] = {}
    config_store_allowed: bool = True

    in_file: bool = False

    # Fields that handle UI actions and functionality
    selected_agent_config_tab: str = "1"
    selected_config_component_id: str = ""
    routing_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "source": self.source,
            "config": self.config,
            "config_store_allowed": self.config_store_allowed,
            "config_store": {
                config["path"]: {
                    "path": config["path"],
                    "data_type": config["data_type"],
                    "value": config["value"]
                }
                # Consider only the valid safe entries in the config store 
                for config in (i.safe_entry for i in self.config_store if i.safe_entry["path"] != "")
            }
        }

class HostEntryModelView(rx.Base):
    id: str = ""
    ansible_user: str = ""
    ansible_host: str = ""
    ansible_port: str = "22"
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
            "ansible_port": self.ansible_port,
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
    # TODO make this functional when federation stuff gets hydrated
    # enable_federation: bool = False

    def to_dict(self) -> dict[str, str]:
        return {
            "instance_name" : self.instance_name,
            "vip_address" : self.vip_address,
            "message_bus" : self.message_bus,
            "options" : []
            # enable_federation: self.enable_federation
        }

class PlatformModelView(rx.Base):
    config: PlatformConfigModelView = PlatformConfigModelView()
    agents: dict[str, AgentModelView] = {}
    in_file: bool = False

    safe_platform: dict[str, Any] = {}
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "agents": {
                agent.identity: agent.to_dict()
                for agent in self.agents.values()
            }
        }
    
class BACnetDeviceModelView(rx.Base):
    pduSource: str
    deviceIdentifier: str
    maxAPDULengthAccepted: int
    segmentationSupported: str
    vendorID: int
    object_name: str
    scanned_ip_target: str
    device_instance: int
    points: list[dict[str, str]] = []