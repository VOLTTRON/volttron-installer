from typing import Literal, List
from typing_extensions import Annotated
import logging

from pydantic import BaseModel, AfterValidator, ValidationError, Field, field_validator

from .validators import is_valid_field_name_for_config
import re

logger = logging.getLogger(__name__)

class HostEntry(BaseModel):
    """
    A `HostEntry` represents a single entry in the inventory.  It is a single
    VOLTTRON instance connection point.
    """
    id: str
    ansible_user: str
    ansible_host: str
    ansible_port: int = Field(default=22)
    ansible_connection: Literal["ssh", "local"] = "ssh"
    http_proxy: str | None = None
    https_proxy: str | None = None
    volttron_venv: str | None = None
    volttron_home: str = "~/.volttron"
    host_configs_dir: str | None = None

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "ansible_user": self.ansible_user,
            "ansible_host": self.ansible_host,
            "https_proxy": self.https_proxy,
            "volttron_venv": self.volttron_venv,
            "host_configs_dir": self.host_configs_dir
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

class CreateOrUpdateHostEntry(BaseModel):
    """Request model for creating or updating a host entry"""
    id: str
    ansible_user: str
    ansible_host: str
    ansible_port: int = Field(default=22)
    http_proxy: str = ""
    https_proxy: str = ""
    volttron_venv: str = ""
    host_configs_dir: str = ""

class RemoveHostEntry(BaseModel):
    """Request model for removing a host entry"""
    id: str
    
class ConfigStoreEntry(BaseModel):
    """Represents an entry in the configuration store"""
    name: str
    content: str

class AgentDefinition(BaseModel):
    identity: str
    agent_source: str
    agent_running: bool = True
    has_config_store: bool = False
    agent_config: dict[str, str] = {}
    agent_config_store: list[ConfigStoreEntry] = []

class PlatformConfiguration(BaseModel):
    """Request model for configuring a platform"""
    instance_name: str
    vip_address: str
    message_bus: Literal["zmq"] = "zmq"
    agents: list[AgentDefinition]

class SuccessResponse(BaseModel):
    """Simple success response model"""
    success: bool = True

class ConfigItem(BaseModel):
    """Represents a configuration item with a key and value"""
    key: Annotated[str, AfterValidator(is_valid_field_name_for_config)]
    value: str

class ConfigStoreEntry(BaseModel):
    """Represents an entry in the configuration store"""
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
    """Represents an agent definition with validation in model_post_init"""
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
    """Represents the platform configuration"""
    instance_name: str = "volttron1"
    vip_address: str = "tcp://127.0.0.1:22916"
    message_bus: Literal["zmq"] = "zmq"

    @field_validator('vip_address')
    def validate_vip_address(cls, v):
        if not re.match(r'^tcp://[\d.]+:\d+$', v):
            raise ValueError("vip_address must be in the format tcp://<ip>:<port>")
        return v

    @field_validator('instance_name')
    def validate_instance_name(cls, v):
        if not re.match(r'^[\w-]+$', v):
            raise ValueError("instance_name must contain only letters, numbers, hyphens, and underscores")
        return v

class PlatformDefinition(BaseModel):
    """Represents the platform definition with methods to add configuration items"""
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

class CreatePlatformRequest(PlatformDefinition):
    """Request model for creating a platform"""
    pass

class ConfigurePlatformRequest(BaseModel):
    """Request model for configuring a platform"""
    id: str

class ConfigureAllPlatformsRequest(BaseModel):
    """Request model for configuring all platforms"""
    pass
