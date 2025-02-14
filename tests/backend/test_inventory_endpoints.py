import pytest
from fastapi.testclient import TestClient
from volttron_installer.backend.endpoints import ansible_router
from volttron_installer.backend.models import Inventory, CreateInventoryRequest
from fastapi import FastAPI

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(ansible_router)
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture
def mock_inventory():
    return Inventory(inventory={
        "host1": {
            "id": "host1",
            "ansible_user": "test_user",
            "ansible_host": "localhost",
            "ansible_port": 22,
            "http_proxy": "",
            "https_proxy": "",
            "volttron_venv": "/path/to/venv",
            "host_configs_dir": "/path/to/configs"
        }
    })

def test_get_inventory(client, mocker, mock_inventory):
    # Mock the read_inventory function
    mock_read = mocker.patch('volttron_installer.backend.endpoints.read_inventory')
    mock_read.return_value = mock_inventory

    # Make request
    response = client.get("/ansible/inventory")

    # Verify response
    assert response.status_code == 200
    inventory_data = response.json()
    assert "inventory" in inventory_data
    assert "host1" in inventory_data["inventory"]
    assert inventory_data["inventory"]["host1"]["ansible_user"] == "test_user"

def test_add_to_inventory(client, mocker, mock_inventory):
    # Mock read and write functions
    mock_read = mocker.patch('volttron_installer.backend.endpoints.read_inventory')
    mock_read.return_value = mock_inventory
    mock_write = mocker.patch('volttron_installer.backend.endpoints.write_inventory')

    # Test data
    new_host = {
        "id": "host2",
        "ansible_user": "new_user",
        "ansible_host": "localhost",
        "ansible_port": 22,
        "http_proxy": "",
        "https_proxy": "",
        "volttron_venv": "/path/to/venv",
        "host_configs_dir": "/path/to/configs"
    }

    # Make request
    response = client.post("/ansible/inventory", json=new_host)

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"success": True}

    # Verify write was called with updated inventory
    mock_write.assert_called_once()
    updated_inventory = mock_write.call_args[0][0]
    assert "host2" in updated_inventory.inventory
    assert updated_inventory.inventory["host2"].ansible_user == "new_user"

def test_add_duplicate_to_inventory(client, mocker, mock_inventory):
    # Mock read and write functions
    mock_read = mocker.patch('volttron_installer.backend.endpoints.read_inventory')
    mock_read.return_value = mock_inventory
    mock_write = mocker.patch('volttron_installer.backend.endpoints.write_inventory')

    # Test data (using existing host1 ID)
    duplicate_host = {
        "id": "host1",
        "ansible_user": "another_user",
        "ansible_host": "localhost",
        "ansible_port": 22,
        "http_proxy": "",
        "https_proxy": "",
        "volttron_venv": "/path/to/venv",
        "host_configs_dir": "/path/to/configs"
    }

    # Make request
    response = client.post("/ansible/inventory", json=duplicate_host)

    # Verify response (should still succeed as it updates existing entry)
    assert response.status_code == 200
    assert response.json() == {"success": True}

    # Verify write was called with updated inventory
    mock_write.assert_called_once()
    updated_inventory = mock_write.call_args[0][0]
    assert updated_inventory.inventory["host1"].ansible_user == "another_user"

def test_remove_from_inventory(client, mocker, mock_inventory):
    # Mock read and write functions
    mock_read = mocker.patch('volttron_installer.backend.endpoints.read_inventory')
    mock_read.return_value = mock_inventory
    mock_write = mocker.patch('volttron_installer.backend.endpoints.write_inventory')

    # Make request to remove existing host
    response = client.delete("/ansible/inventory/host1")

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"success": True}

    # Verify write was called with updated inventory
    mock_write.assert_called_once()
    updated_inventory = mock_write.call_args[0][0]
    assert "host1" not in updated_inventory.inventory

def test_remove_nonexistent_from_inventory(client, mocker, mock_inventory):
    # Mock read and write functions
    mock_read = mocker.patch('volttron_installer.backend.endpoints.read_inventory')
    mock_read.return_value = mock_inventory
    mock_write = mocker.patch('volttron_installer.backend.endpoints.write_inventory')

    # Make request to remove non-existent host
    response = client.delete("/ansible/inventory/nonexistent")

    # Verify response (should still succeed)
    assert response.status_code == 200
    assert response.json() == {"success": True}

    # Since we're not modifying anything (host doesn't exist),
    # we don't need to verify write was called
    mock_write.assert_not_called()

def test_get_empty_inventory(client, mocker):
    # Mock read function to return empty inventory
    mock_read = mocker.patch('volttron_installer.backend.endpoints.read_inventory')
    mock_read.return_value = Inventory(inventory={})

    # Make request
    response = client.get("/ansible/inventory")

    # Verify response
    assert response.status_code == 200
    inventory_data = response.json()
    assert inventory_data == {"inventory": {}}
