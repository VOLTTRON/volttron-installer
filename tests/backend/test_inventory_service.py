import pytest
import yaml
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from volttron_installer.backend.services.inventory_service import InventoryService
from volttron_installer.backend.models import HostEntry

@pytest.fixture
def temp_inventory_file():
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        yield Path(temp_file.name)
    temp_file.unlink()

@pytest.fixture
def inventory_service(temp_inventory_file):
    return InventoryService(inventory_path=temp_inventory_file)

@pytest.fixture
def host_entry():
    return HostEntry(id="host1", ansible_user="foo", ansible_host="192.168.1.1", name = "host1")

@pytest.mark.asyncio
async def test_create_host(inventory_service, host_entry):
    await inventory_service.create_host(host_entry)
    with inventory_service._lock:
        assert "host1" in inventory_service._internal_state['all']['hosts']
        assert inventory_service._internal_state['all']['hosts']['host1'] == host_entry.model_dump()

@pytest.mark.asyncio
async def test_create_host_persists_to_file(inventory_service, host_entry):
    await inventory_service.create_host(host_entry)
    with inventory_service._lock:
        persisted_data = yaml.safe_load(inventory_service._inventory_path.open())
        assert "host1" in persisted_data['all']['hosts']
        assert persisted_data['all']['hosts']['host1'] == host_entry.model_dump()

@pytest.mark.asyncio
async def test_remove_host(inventory_service, host_entry):
    await inventory_service.create_host(host_entry)
    await inventory_service.remove_host(host_entry.id)
    with inventory_service._lock:
        assert "host1" not in inventory_service._internal_state['all']['hosts']

@pytest.mark.asyncio
async def test_remove_host_persists_to_file(inventory_service, host_entry):
    await inventory_service.create_host(host_entry)
    await inventory_service.remove_host(host_entry.id)
    with inventory_service._lock:
        persisted_data = yaml.safe_load(inventory_service._inventory_path.open())
        assert "host1" not in persisted_data['all']['hosts']

@pytest.mark.asyncio
async def test_get_hosts(inventory_service, host_entry):
    await inventory_service.create_host(host_entry)
    hosts = await inventory_service.get_hosts()
    assert "host1" in hosts
    assert hosts["host1"] == host_entry

@pytest.mark.asyncio
async def test_clear(inventory_service, host_entry):
    await inventory_service.create_host(host_entry)
    await inventory_service.clear()
    with inventory_service._lock:
        assert not inventory_service._internal_state['all']['hosts']

@pytest.mark.asyncio
async def test_update_host(inventory_service, host_entry):
    await inventory_service.create_host(host_entry)
    updated_entry = HostEntry(id="host1", ansible_user="bar", ansible_host="192.168.1.2")
    await inventory_service.update_host("host1", updated_entry)
    with inventory_service._lock:
        assert inventory_service._internal_state['all']['hosts']['host1'] == updated_entry.model_dump()

@pytest.mark.asyncio
async def test_get_host_ids(inventory_service, host_entry):
    await inventory_service.create_host(host_entry)
    host_ids = await inventory_service.get_host_ids()
    assert "host1" in host_ids

@pytest.mark.asyncio
async def test_create_host(inventory_service):
    host_entry = HostEntry(id="test_host", ansible_user="user", ansible_host="127.0.0.1")
    await inventory_service.create_host(host_entry)
    retrieved_host = await inventory_service.get_host("test_host")
    assert retrieved_host is not None
    assert retrieved_host.id == "test_host"

@pytest.mark.asyncio
async def test_remove_host(inventory_service):
    host_entry = HostEntry(id="test_host", ansible_user="user", ansible_host="127.0.0.1", name ="test_host" )
    await inventory_service.create_host(host_entry)
    await inventory_service.remove_host("test_host")
    retrieved_host = await inventory_service.get_host("test_host")
    assert retrieved_host is None

@pytest.mark.asyncio
async def test_get_host(inventory_service):
    host_entry = HostEntry(id="test_host", ansible_user="user", ansible_host="127.0.0.1",name="test_host")
    await inventory_service.create_host(host_entry)
    retrieved_host = await inventory_service.get_host("test_host")
    assert retrieved_host is not None
    assert retrieved_host.id == "test_host"

@pytest.mark.asyncio
async def test_get_hosts(inventory_service):
    host_entry1 = HostEntry(id="test_host1", ansible_user="user1", ansible_host="127.0.0.1", name = "test_host1")
    host_entry2 = HostEntry(id="test_host2", ansible_user="user2", ansible_host="127.0.0.2", name = "test_host2")
    await inventory_service.create_host(host_entry1)
    await inventory_service.create_host(host_entry2)
    hosts = await inventory_service.get_hosts()
    assert len(hosts) == 2
    assert "test_host1" in hosts
    assert "test_host2" in hosts

@pytest.mark.asyncio
async def test_clear_inventory(inventory_service):
    host_entry = HostEntry(id="test_host", ansible_user="user", ansible_host="127.0.0.1")
    await inventory_service.create_host(host_entry)
    await inventory_service.clear()
    hosts = await inventory_service.get_hosts()
    assert len(hosts) == 0

@pytest.mark.asyncio
async def test_update_host(inventory_service):
    host_entry = HostEntry(id="test_host", ansible_user="user", ansible_host="127.0.0.1", name="test_host")
    await inventory_service.create_host(host_entry)
    updated_host_entry = HostEntry(id="test_host", ansible_user="new_user", ansible_host="127.0.0.1", name="test_host")
    await inventory_service.update_host("test_host", updated_host_entry)
    retrieved_host = await inventory_service.get_host("test_host")
    assert retrieved_host is not None
    assert retrieved_host.ansible_user == "new_user"
