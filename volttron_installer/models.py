import reflex as rx
from loguru import logger
from .model_views import HostEntryModelView, PlatformModelView

class Instance(rx.Base):
    # TODO: Implement a system to check the platform,
    # config's uncaught changes as well
    host: HostEntryModelView
    platform: PlatformModelView

    web_bind_address: str = "http://127.0.0.1:8080"

    safe_host_entry: dict = {}
    uncaught: bool = False
    valid: bool = False    

    web_checked: bool = False
    advanced_expanded: bool = False
    agent_configuration_expanded: bool = False

    new_instance: bool = True

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