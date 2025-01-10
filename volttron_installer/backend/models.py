from typing import Literal
from typing_extensions import Annotated

from pydantic import BaseModel, AfterValidator, ValidationError

from .validators import is_valid_field_name_for_config


class InventoryItem(BaseModel):
    id: str
    ansible_user: str
    ansible_host: str = "localhost"
    ansible_port: int = 22
    ansible_connection: Literal["local", "ssh"] = "local"
    http_proxy: str | None = None
    https_proxy: str | None = None
    volttron_venv: str | None = None
    host_configs_dir: str | None = None


class Inventory(BaseModel):
    inventory: dict[str, InventoryItem] = {}


class InventoryRequest(InventoryItem):
    pass

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

class AgentDefinition(BaseModel):
    identity: str
    state: str = "present"
    running: bool = True
    enabled: bool = False
    tag: str | None = None
    pypi_package: str | None = None
    source: str | None = None
    config_store: dict[str, ConfigStoreEntry] = {}

    def model_post_init(self, __context):
        if self.pypi_package is None and self.source is None:
            raise ValidationError("Either pypi_package or source must be set.")
        elif self.pypi_package is not None and self.source is not None:
            raise ValidationError("Only one of pypi_package or source can be set.")


class PlatformConfig(BaseModel):
    instance_name: str = "volttron1"
    vip_address: str = "tcp://127.0.0.1:22916"
    message_bus: str = "zmq"



class PlatformDefinition(BaseModel):
    config: PlatformConfig
    agents: dict[str, AgentDefinition] = {}

    def __getitem__(self, item):
        return self.config[item]

    def add_item(self, item: ConfigItem):
        self.config[item.key] = item

    def add(self, key: str, value: str):
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
