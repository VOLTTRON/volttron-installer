from typing import Literal, List, Optional
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
            "ansible_port": int(self.ansible_port),
            "ansible_connection": self.ansible_connection,
            "http_proxy": "" if self.http_proxy is None else self.http_proxy,
            "https_proxy": "" if self.https_proxy is None else self.https_proxy,
            "volttron_venv": "" if self.volttron_venv is None else self.volttron_venv,
            "volttron_home": self.volttron_home,
            "host_configs_dir": "" if self.host_configs_dir is None else self.host_configs_dir
        }


class CreateOrUpdateHostEntryRequest(HostEntry):
    """Request model for creating or updating a host entry"""
    pass

class RemoveHostEntryRequest(BaseModel):
    """Request model for removing a host entry"""
    id: str
    
class ConfigStoreEntry(BaseModel):
    """Represents an entry in the configuration store"""
    # path: Annotated[str, AfterValidator(is_valid_field_name_for_config)]
    path: str
    data_type: Literal["CSV", "JSON"] = "JSON"
    value: str = ""

    def to_dict(self)-> dict[str, str]:
        return {
            "path" : self.path,
            "data_type": self.data_type,
            "value": self.value
        }

class SuccessResponse(BaseModel):
    """Simple success response model"""
    success: bool = True
    object: BaseModel = None

class AgentDefinition(BaseModel):
    """Represents an agent definition with validation in model_post_init"""
    identity: str
    state: str = "present"
    running: bool = True
    enabled: bool = False
    tag: str | None = None
    pypi_package: str | None = None
    source: str | None = None
    config: str | None = None
    config_store: dict[str, ConfigStoreEntry] = {}
    config_store_allowed: bool = True

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

class CreateAgentRequest(BaseModel):
    """Request model for creating an agent"""
    identity: str
    source: str | None = None
    pypi_package: str | None = None
    config_store: dict[str, ConfigStoreEntry] = {}

    def model_post_init(self, __context):
        if self.pypi_package is None and self.source is None:
            logger.error(f"Agent {self.identity}: Neither pypi_package nor source is set")
            raise ValidationError("Either pypi_package or source must be set.")
        elif self.pypi_package is not None and self.source is not None:
            logger.error(f"Agent {self.identity}: Both pypi_package and source are set")
            raise ValidationError("Only one of pypi_package or source can be set.")
        logger.debug(f"Initialized agent creation request for {self.identity}")

class AgentType(BaseModel):
    """Represents a type of agent with default configurations"""
    identity: str
    default_config: dict
    default_config_store: dict[str, ConfigStoreEntry]
    source: str | None = None
    pypi_package: str | None = None
    config_store_allowed: bool = True

class AgentCatalog(BaseModel):
    """Catalog of default agents available with default configurations"""
    agents: dict[str, AgentType] = {
        "listener": AgentType(
            identity="listener",
            default_config={
                "agentid": "listener",
                "message": "Hello, World!",
                "log-level": "INFO"
            },
            default_config_store={},
            config_store_allowed=False,
            source="examples/ListenerAgent"
        ),
        "platform.driver": AgentType(
            identity="platform.driver",
            default_config={
                "driver_scrape_interval": 0.05,
                "publish_breadth_first_all": False,
                "publish_depth_first": False,
                "publish_breadth_first": False
            },
            default_config_store={
                "fake.csv": ConfigStoreEntry(
                    path="fake.csv",
                    data_type="CSV",
                    value="""Point Name,Volttron Point Name,Units,Units Details,Writable,Starting Value,Type,Notes
Heartbeat,Heartbeat,On/Off,On/Off,TRUE,0,boolean,Point for heartbeat toggle
EKG,EKG,waveform,waveform,TRUE,1,float,Sine wave for baseline output
OutsideAirTemperature1,OutsideAirTemperature1,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.0 ppm
SampleWritableFloat1,SampleWritableFloat1,PPM,1000.00 (default),TRUE,10,float,Setpoint to enable demand control ventilation
SampleLong1,SampleLong1,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch
SampleWritableShort1,SampleWritableShort1,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode
SampleBool1,SampleBool1,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1
SampleWritableBool1,SampleWritableBool1,On / Off,on/off,TRUE,TRUE,boolean,Status indicator
OutsideAirTemperature2,OutsideAirTemperature2,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.0 ppm
SampleWritableFloat2,SampleWritableFloat2,PPM,1000.00 (default),TRUE,10,float,Setpoint to enable demand control ventilation
SampleLong2,SampleLong2,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch
SampleWritableShort2,SampleWritableShort2,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode
SampleBool2,SampleBool2,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1
SampleWritableBool2,SampleWritableBool2,On / Off,on/off,TRUE,TRUE,boolean,Status indicator
OutsideAirTemperature3,OutsideAirTemperature3,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.0 ppm
SampleWritableFloat3,SampleWritableFloat3,PPM,1000.00 (default),TRUE,10,float,Setpoint to enable demand control ventilation
SampleLong3,SampleLong3,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch
SampleWritableShort3,SampleWritableShort3,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode
SampleBool3,SampleBool3,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1
SampleWritableBool3,SampleWritableBool3,On / Off,on/off,TRUE,TRUE,boolean,Status indicator
HPWH_Phy0_PowerState,PowerState,1/0,1/0,TRUE,0,int,Power on off status
ERWH_Phy0_ValveState,ValveState,1/0,1/0,TRUE,0,int,power on off status
EKG_Sin,EKG_Sin,1-0,SIN Wave,TRUE,0,float,SIN wave
EKG_Cos,EKG_Cos,1-0,COS Wave,TRUE,0,float,COS wave"""),
                "devices/fake/driver": ConfigStoreEntry(
                    path="fake.json",
                    data_type="JSON",
                    value="""{
                        "driver_config": {},
                        "registry_config":"config://fake.csv",
                        "interval": 5,
                        "timezone": "US/Pacific",
                        "heart_beat_point": "Heartbeat",
                        "driver_type": "fakedriver",
                        "publish_breadth_first_all": false,
                        "publish_depth_first": false,
                        "publish_breadth_first": false,
                        "campus": "campus",
                        "building": "building",
                        "unit": "fake_device"
                    }""")
            },
            source="services/core/PlatformDriverAgent"
        )
    }

    def get_agent(self, identity: str) -> Optional[AgentType]:
        return self.agents.get(identity)

class KeyValuePair(BaseModel):
    key: str
    value: float | int | str


class PlatformConfig(BaseModel):
    """Represents the platform configuration"""
    instance_name: str = "volttron1"
    vip_address: str = "tcp://127.0.0.1:22916"
    message_bus: Literal["zmq"] = "zmq"
    options: list[KeyValuePair] = []

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
    """
    Represents the platform definition with methods to add configuration items.
    
    Attributes:
        host_id (str): A reference to the `id` field of a `HostEntry` instance, 
                       representing a unique VOLTTRON instance connection point.
        config (PlatformConfig): The configuration specific to the platform.
        agents (dict[str, AgentDefinition]): A dictionary mapping agent names 
                                             to their definitions.
    """
    host_id: str
    config: PlatformConfig = PlatformConfig()
    agents: dict[str, AgentDefinition] = {}

    def __getitem__(self, item):
        return self.config[item]

class CreatePlatformRequest(PlatformDefinition):
    """Request model for creating a platform"""
    pass

class AgentStatus(BaseModel):
    """Represents the state of an agent"""
    identity: str
    state: Literal["not deployed", "deployed", "started", "stopped"] = "not deployed"
    
class PlatformDeploymentStatus(BaseModel):
    """Represents the state of a platform deployment"""
    platform_id: str
    host_configured: bool = False
    keys_verified: bool = False
    state: Literal["not deployed", "deployed", "running"] = "not deployed"
    agents: dict[str, AgentStatus] = {}

class DeployPlatformRequest(BaseModel):
    """Request model for deploying a platform"""
    platform_id: str

class PlatformDeplymentStatusRequest(BaseModel):
    """Request model for getting the state of a platform deployment"""
    platform_id: str