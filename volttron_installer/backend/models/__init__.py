"""Backend data models — re-exports from domain-specific modules for backward compatibility."""

from .host import HostEntry, CreateOrUpdateHostEntryRequest, RemoveHostEntryRequest, ReachableResponse
from .tool import ToolRequest, ToolStatusResponse, ConfigStoreEntry, SuccessResponse
from .agent import AgentDefinition, CreateAgentRequest, AgentType
from .agent_catalog import AgentCatalog, GitHubAgentsResponse
from .platform import (
    KeyValuePair,
    PlatformConfig,
    PlatformDefinition,
    CreatePlatformRequest,
    AgentStatus,
    PlatformDeploymentStatus,
    DeployPlatformRequest,
    PlatformDeplymentStatusRequest,
)
from .bacnet import (
    BACnetDevice,
    BACnetScanResults,
    BACnetReadPropertyRequest,
    BACnetWritePropertyRequest,
    BACnetReadDeviceAllRequest,
    BACnetReadObjectListRequest,
)
from .driver import DriverLibrary, DriverLibraryCatalog

__all__ = [
    "HostEntry",
    "CreateOrUpdateHostEntryRequest",
    "RemoveHostEntryRequest",
    "ReachableResponse",
    "ToolRequest",
    "ToolStatusResponse",
    "ConfigStoreEntry",
    "SuccessResponse",
    "AgentDefinition",
    "CreateAgentRequest",
    "AgentType",
    "AgentCatalog",
    "GitHubAgentsResponse",
    "KeyValuePair",
    "PlatformConfig",
    "PlatformDefinition",
    "CreatePlatformRequest",
    "AgentStatus",
    "PlatformDeploymentStatus",
    "DeployPlatformRequest",
    "PlatformDeplymentStatusRequest",
    "BACnetDevice",
    "BACnetScanResults",
    "BACnetReadPropertyRequest",
    "BACnetWritePropertyRequest",
    "BACnetReadDeviceAllRequest",
    "BACnetReadObjectListRequest",
    "DriverLibrary",
    "DriverLibraryCatalog",
]