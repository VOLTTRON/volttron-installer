from pathlib import Path

import yaml

from ..settings import get_settings
from .transformers import normalize_file_name
from .models import Inventory, InventoryItem, PlatformDefinition, ConfigItem

def __get_path__(path: Path | None = None) -> Path:
    if path is None:
        path = Path(get_settings().data_dir) / "inventory.yml"

    return path


def read_inventory(path: Path | None = None) -> Inventory:
    if path is None:
        path = Path(get_settings().data_dir) / "inventory.yml"

        #raise FileNotFoundError(f"Inventory file not found at {path}")
    if not path.exists():
        return Inventory()
    inv_obj = Inventory()
    data = yaml.safe_load(path.read_text())
    for k, v in data["all"]["hosts"].items():
        inv_obj.inventory[k] = InventoryItem.parse_obj(v)
    return inv_obj


def write_inventory(inventory: Inventory, path: Path | None = None):
    if path is None:
        path = Path(get_settings().data_dir) / "inventory.yml"

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, dict] = {"all": {"hosts": {}}}

    for k, v in inventory.inventory.items():
        data["all"]["hosts"][k] = v.dict()

    path.write_text(yaml.dump(data))


def write_platform_file(platform: PlatformDefinition, path: Path | None = None):
    if path is None:
        path = Path(get_settings().data_dir) / "platforms" / f"{normalize_file_name(platform.name)}" / f"{normalize_file_name(platform.name)}.yml"

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    data = platform.dict()
    path.write_text(yaml.dump(data))
