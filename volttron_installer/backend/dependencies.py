from pathlib import Path
import json
import os
import fcntl
from contextlib import contextmanager
from typing import Any

import yaml

from ..settings import get_settings
from .transformers import normalize_file_name
from .models import Inventory, InventoryItem, PlatformDefinition, ConfigItem

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
    return Path(os.getenv("INVENTORY_FILE", "inventory.json"))


def read_inventory() -> Inventory:
    path = get_inventory_path()
    if not path.exists():
        return Inventory(inventory={})

    try:
        with open(path, 'r') as f:
            with file_lock(f):
                data = json.load(f)
                return Inventory.model_validate(data)
    except json.JSONDecodeError:
        return Inventory(inventory={})
    except Exception as e:
        raise ValueError(f"Error reading inventory: {str(e)}")


def write_inventory(inventory: Inventory, merge: bool = True) -> None:
    """Write inventory to file with optional merging

    Args:
        inventory: The inventory to write
        merge: If True, merge with existing inventory. If False, overwrite.
    """
    path = get_inventory_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if merge:
        try:
            with open(path, 'r+') as f:
                with file_lock(f, exclusive=True):
                    try:
                        current = json.load(f)
                        current_inventory = Inventory.model_validate(current)
                        current_inventory.inventory.update(inventory.inventory)
                        f.seek(0)
                        f.truncate()
                        json.dump(current_inventory.model_dump(), f, indent=2)
                    except json.JSONDecodeError:
                        # If file is corrupted, just write new inventory
                        f.seek(0)
                        f.truncate()
                        json.dump(inventory.model_dump(), f, indent=2)
        except FileNotFoundError:
            # If file doesn't exist, create it
            with open(path, 'w') as f:
                with file_lock(f, exclusive=True):
                    json.dump(inventory.model_dump(), f, indent=2)
    else:
        # Direct overwrite without merging
        with open(path, 'w') as f:
            with file_lock(f, exclusive=True):
                json.dump(inventory.model_dump(), f, indent=2)


def write_platform_file(platform: PlatformDefinition, path: Path | None = None):
    if path is None:
        path = Path(get_settings().data_dir) / "platforms" / f"{normalize_file_name(platform.name)}" / f"{normalize_file_name(platform.name)}.yml"

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    data = platform.dict()
    path.write_text(yaml.dump(data))
