import reflex as rx
from loguru import logger
from .model_views import HostEntryModelView, PlatformModelView

class Instance(rx.Base):
    # TODO: Implement a system to check the platform,
    # config's uncaught changes as well
    host: HostEntryModelView
    platform: PlatformModelView

    web_bind_address: str = "http://127.0.0.1:8080"
    password: str = ""

    safe_host_entry: dict = {}
    uncaught: bool = False
    valid: bool = False    

    # UI vars
    web_checked: bool = False
    federation_checked: bool = False
    advanced_expanded: bool = False
    agent_configuration_expanded: bool = False

    new_instance: bool = True
    deployed: bool = False

    def has_uncaught_changes(self) -> bool:
        return self.host.to_dict() != self.safe_host_entry

    def does_host_have_errors(self) -> bool:
        host_dict = self.host.to_dict()
        if not all([host_dict.get("id"), host_dict.get("ansible_user"), host_dict.get("ansible_host")]):
            logger.debug(f"Error: Missing host details {host_dict}")
        # If all fields are filled out, return false because no errors
        return (
            host_dict["id"] and \
            host_dict["ansible_user"] and \
            host_dict["ansible_host"] != ""
        )

    def refresh_for_copy(self) -> None:
        """
        Refresh the instance for copying.
        """
        self.new_instance = True
        self.platform.in_file = False
        self.deployed = False
        self.password = ""
        for agent in self.platform.agents.values():
            agent.in_file = False
            agent.selected_config_component_id = ""
            agent.selected_agent_config_tab="1"
            for config in agent.config_store:
                config.in_file = False
                config.selected_cell = ""

class Tool(rx.Base):
    name: str = ""
    module_path: str = ""
    use_poetry: bool = False

class RequestWhoIsModel(rx.Model):
    device_instance_low: str = ""
    device_instance_high: str = "" 
    dest: str = ""

class ReadDeviceAllModel(rx.Model):
    device_address: str = ""
    device_object_identifier: str = ""

class ScanIPRangeModel(rx.Model):
    network_string: str = ""

class PingIPModel(rx.Model):
    ip_address: str = ""

class ReadPropertyModel(rx.Model):
    device_address: str = ""
    object_identifier: str = ""
    property_identifier: str = ""
    property_array_index: str | int = ""

class WritePropertyModel(rx.Model):
    device_address: str = ""
    object_identifier: str = ""
    property_identifier: str = ""
    value: str = ""
    priority: str | int = ""
    property_array_index: str | int = ""

class WindowsHostIPModel(rx.Base):
    windows_host_ip: str = "" 

class LocalIPModel(rx.Base):
    local_ip: str = ""
    subnet_mask: str = ""
    cidr: str = ""