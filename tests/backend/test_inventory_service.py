import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock
from volttron_installer.backend.services.inventory_service import InventoryService
from volttron_installer.backend.models import HostEntry

@pytest.fixture
def inventory_service(tmp_path):
    inventory_path = tmp_path / "inventory.yml"
    return InventoryService(inventory_path)

@pytest.fixture
def host_entry():
    return HostEntry(id="host1", ansible_user="foo", ansible_host="192.168.1.1")

@pytest.mark.asyncio
async def test_add_host(inventory_service, host_entry):
    await inventory_service.add_host(host_entry)
    with inventory_service._lock:
        assert "host1" in inventory_service._internal_state['all']['hosts']
        assert inventory_service._internal_state['all']['hosts']['host1'] == host_entry.model_dump()

@pytest.mark.asyncio
async def test_add_host_persists_to_file(inventory_service, host_entry):
    await inventory_service.add_host(host_entry)
    with inventory_service._lock:
        persisted_data = yaml.safe_load(inventory_service._inventory_path.open())
        assert "host1" in persisted_data['all']['hosts']
        assert persisted_data['all']['hosts']['host1'] == host_entry.model_dump()

@pytest.mark.asyncio
async def test_remove_host(inventory_service, host_entry):
    await inventory_service.add_host(host_entry)
    await inventory_service.remove_host(host_entry.id)
    with inventory_service._lock:
        assert "host1" not in inventory_service._internal_state['all']['hosts']

@pytest.mark.asyncio
async def test_remove_host_persists_to_file(inventory_service, host_entry):
    await inventory_service.add_host(host_entry)
    await inventory_service.remove_host(host_entry.id)
    with inventory_service._lock:
        persisted_data = yaml.safe_load(inventory_service._inventory_path.open())
        assert "host1" not in persisted_data['all']['hosts']

@pytest.mark.asyncio
async def test_get_hosts(inventory_service, host_entry):
    await inventory_service.add_host(host_entry)
    hosts = await inventory_service.get_hosts()
    assert "host1" in hosts
    assert hosts["host1"] == host_entry

@pytest.mark.asyncio
async def test_clear(inventory_service, host_entry):
    await inventory_service.add_host(host_entry)
    await inventory_service.clear()
    with inventory_service._lock:
        assert not inventory_service._internal_state['all']['hosts']

@pytest.mark.asyncio
async def test_update_host(inventory_service, host_entry):
    await inventory_service.add_host(host_entry)
    updated_entry = HostEntry(id="host1", ansible_user="bar", ansible_host="192.168.1.2")
    await inventory_service.update_host("host1", updated_entry)
    with inventory_service._lock:
        assert inventory_service._internal_state['all']['hosts']['host1'] == updated_entry.model_dump()

@pytest.mark.asyncio
async def test_get_host_ids(inventory_service, host_entry):
    await inventory_service.add_host(host_entry)
    host_ids = await inventory_service.get_host_ids()
    assert "host1" in host_ids
