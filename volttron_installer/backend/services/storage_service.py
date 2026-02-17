"""
JSON-based storage service for VOLTTRON instances.
Replaces YAML file-per-instance with a single JSON file for better performance.
"""
from pathlib import Path
import asyncio
import json
from typing import Optional
from datetime import datetime

import aiofiles

from volttron_installer.backend.models import PlatformDefinition
from volttron_installer.settings import get_settings
from loguru import logger


class StorageService:
    """Handles persistence of platform instances to a single JSON file."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(get_settings().data_dir)
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.data_dir / "instances.json"
        self._lock = asyncio.Lock()
        logger.info(f"StorageService initialized with storage file: {self.storage_file}")

    async def initialize(self):
        """Create storage file if it doesn't exist."""
        if not self.storage_file.exists():
            logger.info("Creating new instances.json file")
            await self._write_storage({
                "version": "1.0",
                "last_modified": datetime.utcnow().isoformat(),
                "instances": []
            })

    async def _read_storage(self) -> dict:
        """Read the entire storage file."""
        try:
            async with aiofiles.open(self.storage_file, 'r') as file:
                content = await file.read()
                return json.loads(content)
        except FileNotFoundError:
            logger.warning("Storage file not found, initializing...")
            await self.initialize()
            return await self._read_storage()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse storage file: {e}")
            raise ValueError(f"Corrupted storage file: {e}")

    async def _write_storage(self, data: dict):
        """Write the entire storage file."""
        data["last_modified"] = datetime.utcnow().isoformat()
        async with aiofiles.open(self.storage_file, 'w') as file:
            await file.write(json.dumps(data, indent=2))
        logger.debug(f"Wrote storage file with {len(data.get('instances', []))} instances")

    async def get_all_platforms(self) -> list[PlatformDefinition]:
        """Get all platform instances."""
        async with self._lock:
            storage = await self._read_storage()
            instances = storage.get("instances", [])
            logger.debug(f"Retrieved {len(instances)} platforms from storage")
            return [PlatformDefinition(**instance) for instance in instances]

    async def get_platform(self, instance_name: str) -> Optional[PlatformDefinition]:
        """Get a single platform by instance name."""
        async with self._lock:
            storage = await self._read_storage()
            instances = storage.get("instances", [])
            
            for instance in instances:
                if instance.get("config", {}).get("instance_name") == instance_name:
                    logger.debug(f"Found platform: {instance_name}")
                    return PlatformDefinition(**instance)
            
            logger.debug(f"Platform not found: {instance_name}")
            return None

    async def create_platform(self, definition: PlatformDefinition):
        """Add a new platform instance."""
        async with self._lock:
            storage = await self._read_storage()
            instances = storage.get("instances", [])
            
            # Check if instance already exists
            instance_name = definition.config.instance_name
            if any(i.get("config", {}).get("instance_name") == instance_name for i in instances):
                raise ValueError(f"Platform {instance_name} already exists")
            
            instances.append(definition.model_dump())
            storage["instances"] = instances
            await self._write_storage(storage)
            logger.info(f"Created platform: {instance_name}")

    async def update_platform(self, instance_name: str, updated_definition: PlatformDefinition):
        """Update an existing platform instance."""
        async with self._lock:
            storage = await self._read_storage()
            instances = storage.get("instances", [])
            
            # Find and update the instance
            found = False
            for i, instance in enumerate(instances):
                if instance.get("config", {}).get("instance_name") == instance_name:
                    instances[i] = updated_definition.model_dump()
                    found = True
                    break
            
            if not found:
                raise FileNotFoundError(f"Platform {instance_name} not found")
            
            storage["instances"] = instances
            await self._write_storage(storage)
            logger.info(f"Updated platform: {instance_name}")

    async def delete_platform(self, instance_name: str):
        """Delete a platform instance."""
        async with self._lock:
            storage = await self._read_storage()
            instances = storage.get("instances", [])
            
            # Filter out the instance to delete
            original_count = len(instances)
            instances = [
                i for i in instances 
                if i.get("config", {}).get("instance_name") != instance_name
            ]
            
            if len(instances) == original_count:
                raise FileNotFoundError(f"Platform {instance_name} not found")
            
            storage["instances"] = instances
            await self._write_storage(storage)
            logger.info(f"Deleted platform: {instance_name}")

    async def platform_exists(self, instance_name: str) -> bool:
        """Check if a platform exists."""
        platform = await self.get_platform(instance_name)
        return platform is not None


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the singleton storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
