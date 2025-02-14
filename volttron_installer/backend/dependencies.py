from pathlib import Path
import json
import os
import fcntl
from contextlib import contextmanager
from typing import Any, Optional

import yaml

from ..settings import get_settings
from .transformers import normalize_file_name
from .models import Inventory, HostEntry, PlatformDefinition, ConfigItem

@contextmanager
def file_lock(file_obj, exclusive=False):
    """Context manager for file locking"""
    try:
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)

def __get_path__(path: Path | None = None) -> Path:
    if path is None:
        path = Path(get_settings().data_dir) / "inventory.yml"

    return path


def get_inventory_path() -> Path:
    """Get the path to the inventory file"""
    inventory_path = os.getenv("INVENTORY_FILE")
    if inventory_path:
        return Path(inventory_path)
    return Path("data/inventory.json")


def read_inventory() -> Inventory:
    """Read inventory from file"""
    inventory_path = get_inventory_path()
    if not inventory_path.exists():
        return Inventory()

    try:
        return Inventory.model_validate_json(inventory_path.read_text())
    except (ValidationError, json.JSONDecodeError):
        # Return empty inventory if file is invalid
        return Inventory()


def write_inventory(inventory: Inventory, merge: bool = False) -> None:
    """Write inventory to file"""
    inventory_path = get_inventory_path()
    inventory_path.parent.mkdir(parents=True, exist_ok=True)

    if merge and inventory_path.exists():
        # Merge with existing inventory
        existing = read_inventory()
        existing.inventory.update(inventory.inventory)
        inventory = existing

    inventory_path.write_text(inventory.model_dump_json(indent=2))


def write_platform_file(platform: PlatformDefinition, path: Path | None = None):
    if path is None:
        path = Path(get_settings().data_dir) / "platforms" / f"{normalize_file_name(platform.name)}" / f"{normalize_file_name(platform.name)}.yml"

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    data = platform.dict()
    path.write_text(yaml.dump(data))
