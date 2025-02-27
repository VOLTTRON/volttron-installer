from pathlib import Path
import asyncio
from typing import Optional

import aiofiles
import yaml

from volttron_installer.backend.models import PlatformDefinition
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
            normalized_name = normalize_name_for_file(definition.config.instance_name)
            definition_path = self.platform_dir / normalized_name
            definition_path.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(definition_path.joinpath(f"{normalized_name}.yml"), 'w') as file:
                await file.write(yaml.dump(definition.model_dump()))

    async def get_platform(self, instance_name: str) -> Optional[PlatformDefinition]:
        async with self._lock:
            normalized_name = normalize_name_for_file(instance_name)
            definition_path = self.platform_dir / instance_name / f"{normalized_name}.yml"
            if definition_path.exists():
                async with aiofiles.open(definition_path, 'r') as file:
                    data = yaml.safe_load(await file.read())
                    return PlatformDefinition(**data)
            return None

    async def update_platform(self, instance_name: str, updated_definition: PlatformDefinition):
        async with self._lock:
            normalized_name = normalize_name_for_file(instance_name)
            definition_path = self.platform_dir / instance_name / f"{normalized_name}.yml"
            if definition_path.exists():
                async with aiofiles.open(definition_path, 'w') as file:
                    await file.write(yaml.dump(updated_definition.model_dump()))
            else:
                raise FileNotFoundError(f"Platform definition for {instance_name} not found.")

    async def delete_platform(self, instance_name: str):
        async with self._lock:
            definition_path = self.platform_dir / instance_name
            if definition_path.exists() and definition_path.is_dir():
                for file in definition_path.glob("*.yml"):
                    file.unlink()
                definition_path.rmdir()
            else:
                raise FileNotFoundError(f"Platform definition for {instance_name} not found.")

    async def get_platform_instance_names(self) -> list[str]:
        async with self._lock:
            return [platform_dir.name for platform_dir in self.platform_dir.iterdir() if platform_dir.is_dir()]

__platform_service__ = PlatformService()

async def get_platform_service():
    return __platform_service__