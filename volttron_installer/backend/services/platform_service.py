from pathlib import Path
import asyncio
from typing import Optional

import aiofiles
import yaml

from volttron_installer.backend.models import PlatformDefinition, AgentDefinition
from volttron_installer.settings import get_settings
from volttron_installer.backend.utils import normalize_name_for_file


class PlatformService:
    def __init__(self, platform_dir: Optional[Path] = None):
        if platform_dir is None:
            platform_dir = Path(get_settings().data_dir) / "platforms"
        self.platform_dir = platform_dir
        self.platform_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()  # Use asyncio.Lock for async operations

    async def create_platform(self, definition: PlatformDefinition):
        async with self._lock:
            await self._create_platform(definition)

    async def _create_platform(self, definition: PlatformDefinition):
        normalized_name = normalize_name_for_file(definition.config.instance_name)
        definition_path = self.platform_dir / normalized_name
        definition_path.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(definition_path.joinpath(f"{normalized_name}.yml"), 'w') as file:
            await file.write(yaml.dump(definition.model_dump()))

    async def get_platform(self, instance_name: str) -> Optional[PlatformDefinition]:
        async with self._lock:
            return await self._get_platform(instance_name)

    async def _get_platform(self, instance_name: str) -> Optional[PlatformDefinition]:
        normalized_name = normalize_name_for_file(instance_name)
        definition_path = self.platform_dir / instance_name / f"{normalized_name}.yml"
        if definition_path.exists():
            async with aiofiles.open(definition_path, 'r') as file:
                data = yaml.safe_load(await file.read())
                return PlatformDefinition(**data)
        return None

    async def update_platform(self, instance_name: str, updated_definition: PlatformDefinition):
        async with self._lock:
            await self._update_platform(instance_name, updated_definition)

    async def _update_platform(self, instance_name: str, updated_definition: PlatformDefinition):
        normalized_name = normalize_name_for_file(instance_name)
        definition_path = self.platform_dir / instance_name / f"{normalized_name}.yml"
        if definition_path.exists():
            async with aiofiles.open(definition_path, 'w') as file:
                await file.write(yaml.dump(updated_definition.model_dump()))
        else:
            raise FileNotFoundError(f"Platform definition for {instance_name} not found.")

    async def delete_platform(self, instance_name: str):
        async with self._lock:
            await self._delete_platform(instance_name)

    async def _delete_platform(self, instance_name: str):
        definition_path = self.platform_dir / instance_name
        if definition_path.exists() and definition_path.is_dir():
            for file in definition_path.glob("*.yml"):
                file.unlink()
            definition_path.rmdir()
        else:
            raise FileNotFoundError(f"Platform definition for {instance_name} not found.")

    async def get_all_platforms(self) -> list[PlatformDefinition]:
        async with self._lock:
            return await self._get_all_platforms()

    async def _get_all_platforms(self) -> list[PlatformDefinition]:
        platforms = []
        for platform_dir in self.platform_dir.iterdir():
            if platform_dir.is_dir():
                definition_path = platform_dir / f"{platform_dir.name}.yml"
                if definition_path.exists():
                    async with aiofiles.open(definition_path, 'r') as file:
                        data = yaml.safe_load(await file.read())
                        platforms.append(PlatformDefinition(**data))
        return platforms

    async def get_platform_instance_names(self) -> list[str]:
        async with self._lock:
            return await self._get_platform_instance_names()

    async def _get_platform_instance_names(self) -> list[str]:
        return [platform_dir.name for platform_dir in self.platform_dir.iterdir() if platform_dir.is_dir()]

    async def create_agent(self, platform_id: str, agent: AgentDefinition):
        async with self._lock:
            await self._create_agent(platform_id, agent)

    async def _create_agent(self, platform_id: str, agent: AgentDefinition):
        platform = await self._get_platform(platform_id)
        if platform is None:
            raise FileNotFoundError(f"Platform {platform_id} not found.")
        platform.agents[agent.identity] = agent
        await self._update_platform(platform_id, platform)

    async def update_agent(self, platform_id: str, agent_id: str, updated_agent: AgentDefinition):
        async with self._lock:
            await self._update_agent(platform_id, agent_id, updated_agent)

    async def _update_agent(self, platform_id: str, agent_id: str, updated_agent: AgentDefinition):
        platform = await self._get_platform(platform_id)
        if platform is None:
            raise FileNotFoundError(f"Platform {platform_id} not found.")
        if agent_id not in platform.agents:
            raise FileNotFoundError(f"Agent {agent_id} not found in platform {platform_id}.")
        platform.agents[agent_id] = updated_agent
        await self._update_platform(platform_id, platform)

    async def delete_agent(self, platform_id: str, agent_id: str):
        async with self._lock:
            await self._delete_agent(platform_id, agent_id)

    async def _delete_agent(self, platform_id: str, agent_id: str):
        platform = await self._get_platform(platform_id)
        if platform is None:
            raise FileNotFoundError(f"Platform {platform_id} not found.")
        if agent_id not in platform.agents:
            raise FileNotFoundError(f"Agent {agent_id} not found in platform {platform_id}.")
        del platform.agents[agent_id]
        await self._update_platform(platform_id, platform)

__platform_service__ = PlatformService()

async def get_platform_service():
    return __platform_service__