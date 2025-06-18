import yaml
import threading
from pathlib import Path
from typing import Dict, Optional

from volttron_installer.settings import get_settings
from ..models import HostEntry


class InventoryService:
    """Service for managing Ansible inventory"""

    def __init__(self, inventory_path: Optional[Path] = None):
        self._inventory_path = inventory_path or Path(get_settings().data_dir) / "inventory.yml"
        
        self._lock = threading.Lock()  # Use threading.Lock instead of asyncio.Lock
                 
        self._internal_state = yaml.safe_load(self._inventory_path.open())
        if not self._internal_state:
            self._internal_state = {'all': {'hosts': {}}}
            yaml.dump(self._internal_state, self._inventory_path.open('w'))

    @property
    def inventory_path(self) -> Path:
        """Get the inventory path, creating the file if it doesn't exist"""
        self._inventory_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._inventory_path.exists():
            yaml.dump({'all': {'hosts': {}}}, self._inventory_path.open('w'))
        return self._inventory_path
    
    async def create_host(self, entry: HostEntry):
        """Add a host to the inventory"""
        with self._lock:
            self._internal_state['all']['hosts'][entry.name] = entry.model_dump()
            yaml.dump(self._internal_state, self.inventory_path.open('w'))
    
    async def remove_host(self, host_id: str):
        """Remove a host from the inventory"""      
        with self._lock:
            entry = self._internal_state['all']['hosts']
            # for e in entry:
            #     if host_id in self._internal_state['all']['hosts'][e]['id']:
            #         del self._internal_state['all']['hosts'][e]
            #         yaml.dump(self._internal_state, self.inventory_path.open('w'))
            if host_id in self._internal_state['all']['hosts']:
                del self._internal_state['all']['hosts'][host_id]
                yaml.dump(self._internal_state, self.inventory_path.open('w'))
    
    async def get_host(self, host_id: str) -> Optional[HostEntry]:
        """Get a host from the inventory"""
        with self._lock:
            entry = self._internal_state['all']['hosts']
            for e in entry:
                if self._internal_state['all']['hosts'][e]['id'] == host_id:
                    host_val = self._internal_state['all']['hosts'][e]
                    return HostEntry.model_validate(host_val)
            return None
        
    async def get_hosts(self) -> Dict[str, HostEntry]:
        """Get all hosts from the inventory"""
        with self._lock:
            return {id: HostEntry.model_validate(entry) for id, entry in self._internal_state['all']['hosts'].items()}
        
    async def clear(self):
        """Clear the inventory"""
        with self._lock:
            self._internal_state['all']['hosts'].clear()
            yaml.dump(self._internal_state, self.inventory_path.open('w'))

    async def update_host(self, host_id: str, entry: HostEntry):
        """Update a host in the inventory"""

        self.remove_host(host_id)

        with self._lock:
            self._internal_state['all']['hosts'][entry.id] = entry.model_dump()
            yaml.dump(self._internal_state, self.inventory_path.open('w'))

    async def get_host_ids(self) -> list[str]:
        """Get all host IDs from the inventory"""
        with self._lock:
            return list(self._internal_state['all']['hosts'].keys())


__inventory_service__: InventoryService = InventoryService()
async def get_inventory_service() -> InventoryService:
    return __inventory_service__

