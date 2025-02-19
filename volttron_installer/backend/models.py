from typing import Literal, List
from typing_extensions import Annotated
import logging

from pydantic import BaseModel, AfterValidator, ValidationError, Field, conint

from .validators import is_valid_field_name_for_config

logger = logging.getLogger(__name__)


class HostEntry(BaseModel):
    """A single host entry in the inventory"""
    id: str
    ansible_user: str
    ansible_host: str
    ansible_port: conint(gt=0, lt=65536) = 22
    http_proxy: str | None = None
    https_proxy: str | None = None
    volttron_venv: str | None = None
    host_configs_dir: str | None = None

    def to_dict(self) -> dict[str, str]:
        return {
            "host_id": self.id,
            "ansible_user": self.ansible_user,
            "ansible_host": self.ansible_host
        }

class Inventory(BaseModel):
    """Inventory model with a dictionary of host entries"""
    host_entries: dict[str, HostEntry] = {}  # Keep using 'inventory' for backward compatibility

    @property
    def hosts(self) -> list[dict]:
        """Get inventory as a list of dicts for UI display"""
        return [
            {
                "id": host.id,
                "ansible_user": host.ansible_user,
                "ansible_host": host.ansible_host,
            }
            for host in self.host_entries.values()
        ]


class CreateInventoryRequest(BaseModel):
    """Request model for creating a new inventory entry"""
    id: str
    ansible_user: str
    ansible_host: str
    ansible_port: conint(gt=0, lt=65536) = 22
    http_proxy: str = ""
    https_proxy: str = ""
    volttron_venv: str = ""
    host_configs_dir: str = ""


class SuccessResponse(BaseModel):
    success: bool = True


class ConfigItem(BaseModel):
    key: Annotated[str, AfterValidator(is_valid_field_name_for_config)]
    value: str


class ConfigStoreEntry(BaseModel):
    path: str
    name: str = ""
    absolute_path: bool = False
    present: bool = True
    data_type: str = ""
    value: str = ""

    def to_dict(self)-> dict[str, str]:
        return {
            "name": self.name,
            "path" : self.path,
            "data_type": self.data_type,
            "value": self.value
        }


class AgentDefinition(BaseModel):
    identity: str
    state: str = "present"
    running: bool = True
    enabled: bool = False
    tag: str | None = None
    pypi_package: str | None = None
    source: str | None = None
    config_store: dict[str, ConfigStoreEntry] = {}

    def to_dict(self) -> dict[str, str]:
        return {
            "identity": self.identity,
            "config_store" : self.config_store
        }

    def model_post_init(self, __context):
        if self.pypi_package is None and self.source is None:
            logger.error(f"Agent {self.identity}: Neither pypi_package nor source is set")
            raise ValidationError("Either pypi_package or source must be set.")
        elif self.pypi_package is not None and self.source is not None:
            logger.error(f"Agent {self.identity}: Both pypi_package and source are set")
            raise ValidationError("Only one of pypi_package or source can be set.")
        logger.debug(f"Initialized agent definition for {self.identity}")


class PlatformConfig(BaseModel):
    instance_name: str = "volttron1"
    vip_address: str = "tcp://127.0.0.1:22916"
    message_bus: str = "zmq"


class PlatformDefinition(BaseModel):
    config: PlatformConfig = PlatformConfig()
    agents: dict[str, AgentDefinition] = {}

    def __getitem__(self, item):
        return self.config[item]

    def add_item(self, item: ConfigItem):
        logger.debug(f"Adding config item: {item.key}={item.value}")
        self.config[item.key] = item

    def add(self, key: str, value: str):
        logger.debug(f"Adding config key-value: {key}={value}")
        self.config[key] = ConfigItem(key=key, value=value)

    # def model_post_init(self, __context):
    #     if self.config_items == {}:
    #         import socket
    #         self.add("message-bus", "zmq")
    #         self.add("instance-name", socket.gethostname())


# class Platform(BaseModel):
#     config: PlatformConfig | None = None
#     #agents: dict[str, Agent] = {}

#     @property
#     def name(self):
#         return self.config["instance-name"].value

#     def model_post_init(self, __context):
#         if self.config is None:
#             self.config = PlatformConfig()


class CreatePlatformRequest(PlatformDefinition):
    pass


class ConfigurePlatformRequest(BaseModel):
    id: str


class ConfigureAllPlatformsRequest(BaseModel):
    pass
