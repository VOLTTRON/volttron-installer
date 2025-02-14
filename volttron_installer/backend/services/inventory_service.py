import json
import threading
from pathlib import Path
from typing import Dict, Optional

class InventoryService:
    """Service for managing Ansible inventory"""

    def __init__(self, inventory_path: Optional[Path] = None):
        self.inventory_path = inventory_path or Path("data/inventory.json")
        self._lock = threading.Lock()  # Use threading.Lock instead of asyncio.Lock

    async def load_inventory(self) -> Dict:
        """Load inventory from file"""
        with self._lock:  # Use 'with' instead of 'async with'
            if not self.inventory_path.exists():
                return {"inventory": {}}

            try:
                return json.loads(self.inventory_path.read_text())
            except json.JSONDecodeError:
                return {"inventory": {}}

    async def save_inventory(self, inventory: Dict) -> None:
        """Save inventory to file"""
        with self._lock:  # Use 'with' instead of 'async with'
            self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
            self.inventory_path.write_text(json.dumps(inventory, indent=2))

    async def add_host(self, host_id: str, host_vars: Dict) -> None:
        """Add a host to the inventory"""
        with self._lock:  # Use 'with' instead of 'async with'
            inventory = await self.load_inventory()
            inventory["inventory"][host_id] = host_vars
            await self.save_inventory(inventory)

    async def remove_host(self, host_id: str) -> None:
        """Remove a host from the inventory"""
        with self._lock:  # Use 'with' instead of 'async with'
            inventory = await self.load_inventory()
            if host_id in inventory["inventory"]:
                del inventory["inventory"][host_id]
                await self.save_inventory(inventory)

    async def get_host(self, host_id: str) -> Optional[Dict]:
        """Get a host from the inventory"""
        with self._lock:  # Use 'with' instead of 'async with'
            inventory = await self.load_inventory()
            return inventory["inventory"].get(host_id)

    async def list_hosts(self) -> Dict:
        """List all hosts in the inventory"""
        with self._lock:  # Use 'with' instead of 'async with'
            return await self.load_inventory()
