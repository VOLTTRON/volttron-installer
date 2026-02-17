from pathlib import Path
import asyncio
from typing import Optional

from volttron_installer.backend.models import PlatformDefinition, AgentDefinition
from volttron_installer.settings import get_settings
from volttron_installer.backend.services.inventory_service import get_inventory_service
from volttron_installer.backend.services.storage_service import get_storage_service
from loguru import logger


class PlatformService:
    """Platform service that delegates to the JSON storage service."""
    
    def __init__(self, platform_dir: Optional[Path] = None):
        # Keep platform_dir for backward compatibility but use storage service
        if platform_dir is None:
            platform_dir = Path(get_settings().data_dir)
        self.platform_dir = platform_dir
        self.storage = get_storage_service()
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the storage service."""
        await self.storage.initialize()

    async def create_platform(self, definition: PlatformDefinition):
        async with self._lock:
            await self._validate_host_id(definition.host_id)
            await self.storage.create_platform(definition)
            logger.info(f"Platform created: {definition.config.instance_name}")

    async def get_platform(self, instance_name: str) -> Optional[PlatformDefinition]:
        return await self.storage.get_platform(instance_name)

    async def update_platform(self, instance_name: str, updated_definition: PlatformDefinition):
        async with self._lock:
            await self._validate_host_id(updated_definition.host_id)
            await self.storage.update_platform(instance_name, updated_definition)
            logger.info(f"Platform updated: {instance_name}")

    async def delete_platform(self, instance_name: str):
        await self.storage.delete_platform(instance_name)
        logger.info(f"Platform deleted: {instance_name}")

    async def get_all_platforms(self) -> list[PlatformDefinition]:
        return await self.storage.get_all_platforms()

    async def get_platform_instance_names(self) -> list[str]:
        platforms = await self.storage.get_all_platforms()
        return [platform.config.instance_name for platform in platforms]

    async def create_agent(self, platform_id: str, agent: AgentDefinition):
        async with self._lock:
            platform = await self.storage.get_platform(platform_id)
            if platform is None:
                raise FileNotFoundError(f"Platform {platform_id} not found.")
            platform.agents[agent.identity] = agent
            await self.storage.update_platform(platform_id, platform)
            logger.info(f"Agent created: {agent.identity} in platform {platform_id}")

    async def update_agent(self, platform_id: str, agent_id: str, updated_agent: AgentDefinition):
        async with self._lock:
            platform = await self.storage.get_platform(platform_id)
            if platform is None:
                raise FileNotFoundError(f"Platform {platform_id} not found.")
            if agent_id not in platform.agents:
                raise FileNotFoundError(f"Agent {agent_id} not found in platform {platform_id}.")
            platform.agents[agent_id] = updated_agent
            await self.storage.update_platform(platform_id, platform)
            logger.info(f"Agent updated: {agent_id} in platform {platform_id}")

    async def delete_agent(self, platform_id: str, agent_id: str):
        async with self._lock:
            platform = await self.storage.get_platform(platform_id)
            if platform is None:
                raise FileNotFoundError(f"Platform {platform_id} not found.")
            if agent_id not in platform.agents:
                raise FileNotFoundError(f"Agent {agent_id} not found in platform {platform_id}.")
            del platform.agents[agent_id]
            await self.storage.update_platform(platform_id, platform)
            logger.info(f"Agent deleted: {agent_id} from platform {platform_id}")

    async def _validate_host_id(self, host_id: str):
        inventory_service = await get_inventory_service()
        host = await inventory_service.get_host(host_id)
        if host is None:
            raise ValueError(f"Host with id {host_id} does not exist.")

__platform_service__ = PlatformService()

async def get_platform_service():
    return __platform_service__