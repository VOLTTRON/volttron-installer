"""Platform data models."""

import re
from typing import Literal, Optional
from pydantic import BaseModel, field_validator

from .agent import AgentDefinition
from .tool import ConfigStoreEntry


class KeyValuePair(BaseModel):
    key: str
    value: float | int | str


class PlatformConfig(BaseModel):
    """Represents the platform configuration"""
    instance_name: str = "volttron1"
    vip_address: str = "tcp://127.0.0.1:22916"
    message_bus: Literal["zmq"] = "zmq"
    volttron_type: Literal["modular", "monolithic"] = "modular"
    # Version of volttron-core to install (e.g., "2.0.0rc20", "git+https://github.com/...")
    # Empty string means latest from PyPI
    volttron_version: str = ""
    # Optional custom Python path (e.g., "~/.pyenv/versions/3.10.14/bin/python3")
    # Empty string means auto-detect
    custom_python_path: str = ""
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
        deployed (bool): Whether this platform has been deployed to the target host.
    """
    host_id: str
    config: PlatformConfig = PlatformConfig()
    agents: dict[str, AgentDefinition] = {}
    deployed: bool = False

    def __getitem__(self, item):
        return self.config[item]


class CreatePlatformRequest(PlatformDefinition):
    """Request model for creating a platform"""
    pass


class AgentStatus(BaseModel):
    """Represents the state of an agent"""
    identity: str
    uuid: str = ""
    name: str = ""
    tag: str = ""
    priority: str = ""
    status: str = ""
    health: str = ""
    state: Literal["running", "stopped", "unknown"] = "unknown"


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