from pathlib import Path
import threading
from typing import Optional

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
        self._lock = threading.Lock()  # Use threading.Lock instead of asyncio.Lock

    def add_platform(self, definition: PlatformDefinition):
        with self._lock:
            normalized_name = normalize_name_for_file(definition.config.instance_name)
            definition_path = self.platform_dir / normalized_name
            definition_path.mkdir(parents=True, exist_ok=True)
            yaml.dump(definition.model_dump(), definition_path.joinpath(f"{normalized_name}.yml").open('w'))

    def get_platform(self, instance_name: str) -> Optional[PlatformDefinition]:
        with self._lock:
            normalized_name = normalize_name_for_file(instance_name)
            definition_path = self.platform_dir / instance_name / f"{normalized_name}.yml"
            if definition_path.exists():
                with definition_path.open('r') as file:
                    data = yaml.safe_load(file)
                    return PlatformDefinition(**data)
            return None

    def update_platform(self, instance_name: str, updated_definition: PlatformDefinition):
        with self._lock:
            normalized_name = normalize_name_for_file(instance_name)
            definition_path = self.platform_dir / instance_name / f"{normalized_name}.yml"
            if definition_path.exists():
                yaml.dump(updated_definition.model_dump(), definition_path.open('w'))
            else:
                raise FileNotFoundError(f"Platform definition for {instance_name} not found.")

    def delete_platform(self, instance_name: str):
        with self._lock:
            definition_path = self.platform_dir / instance_name
            if definition_path.exists() and definition_path.is_dir():
                for file in definition_path.glob("*.yml"):
                    file.unlink()
                definition_path.rmdir()
            else:
                raise FileNotFoundError(f"Platform definition for {instance_name} not found.")

    def get_platform_instance_names(self) -> list[str]:
        with self._lock:
            return [platform_dir.name for platform_dir in self.platform_dir.iterdir() if platform_dir.is_dir()]

__platform_service__ = PlatformService()

def get_platform_service():
    return __platform_service__