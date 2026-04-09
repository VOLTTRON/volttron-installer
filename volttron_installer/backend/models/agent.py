"""Agent data models."""

import logging
from pydantic import BaseModel, ValidationError

from .tool import ConfigStoreEntry

logger = logging.getLogger(__name__)


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
    default_config: dict | str
    default_config_store: dict[str, ConfigStoreEntry]
    source: str | None = None  # pip package name for modular VOLTTRON
    monolithic_source: str | None = None  # relative path in VOLTTRON codebase for monolithic
    pypi_package: str | None = None
    config_store_allowed: bool = True
    is_local: bool = False  # True for local workspace agents
    local_path: str | None = None  # absolute path to local agent directory