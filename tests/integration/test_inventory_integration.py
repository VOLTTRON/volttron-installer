import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from volttron_installer.backend.endpoints import ansible_router
from volttron_installer.backend.models import Inventory, CreateInventoryRequest, InventoryItem
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
def test_data_dir(tmp_path):
    """Create a temporary directory for test data"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir

@pytest.fixture
def inventory_file(test_data_dir):
    """Create a temporary inventory file with test data"""
    inventory_path = test_data_dir / "inventory.json"

    # Initial test inventory using the correct model
    test_inventory = Inventory(inventory={
        "test_host": InventoryItem(
            id="test_host",
            ansible_user="test_user",
            ansible_host="localhost",
            ansible_port=22,
            http_proxy="",
            https_proxy="",
            volttron_venv="/test/venv",
            host_configs_dir="/test/configs"
        )
    })

    inventory_path.write_text(json.dumps(test_inventory.model_dump()))
    return inventory_path

@pytest.fixture
def mock_inventory_path(monkeypatch, inventory_file):
    """Mock the inventory file path in the application"""
    monkeypatch.setenv("INVENTORY_FILE", str(inventory_file))
    return inventory_file

def test_full_inventory_workflow(client, mock_inventory_path):
    """Test the complete inventory workflow: get, add, update, delete"""

    # 1. Get initial inventory
    response = client.get("/ansible/inventory")
    assert response.status_code == 200
    initial_inventory = response.json()
    assert "test_host" in initial_inventory["inventory"]

    # 2. Add new host
    new_host = {
        "id": "new_host",
        "ansible_user": "new_user",
        "ansible_host": "127.0.0.1",
        "ansible_port": 2222,
        "http_proxy": "http://proxy:8080",
        "https_proxy": "https://proxy:8443",
        "volttron_venv": "/new/venv",
        "host_configs_dir": "/new/configs"
    }

    response = client.post("/ansible/inventory", json=new_host)
    assert response.status_code == 200

    # Verify new host was added
    response = client.get("/ansible/inventory")
    updated_inventory = response.json()
    assert "new_host" in updated_inventory["inventory"]
    assert updated_inventory["inventory"]["new_host"]["ansible_user"] == "new_user"

    # 3. Update existing host
    updated_host = {
        "id": "test_host",
        "ansible_user": "updated_user",
        "ansible_host": "localhost",
        "ansible_port": 2222,
        "http_proxy": "",
        "https_proxy": "",
        "volttron_venv": "/updated/venv",
        "host_configs_dir": "/updated/configs"
    }

    response = client.post("/ansible/inventory", json=updated_host)
    assert response.status_code == 200

    # Verify host was updated
    response = client.get("/ansible/inventory")
    updated_inventory = response.json()
    assert updated_inventory["inventory"]["test_host"]["ansible_user"] == "updated_user"
    assert updated_inventory["inventory"]["test_host"]["volttron_venv"] == "/updated/venv"

    # 4. Delete host
    response = client.delete("/ansible/inventory/new_host")
    assert response.status_code == 200

    # Verify host was deleted
    response = client.get("/ansible/inventory")
    final_inventory = response.json()
    assert "new_host" not in final_inventory["inventory"]
    assert "test_host" in final_inventory["inventory"]  # Original host still exists

def test_inventory_file_persistence(client, mock_inventory_path):
    """Test that inventory changes are properly persisted to file"""

    # Add new host
    new_host = {
        "id": "persistent_host",
        "ansible_user": "persist_user",
        "ansible_host": "localhost",
        "ansible_port": 22,
        "http_proxy": "",
        "https_proxy": "",
        "volttron_venv": "/persist/venv",
        "host_configs_dir": "/persist/configs"
    }

    response = client.post("/ansible/inventory", json=new_host)
    assert response.status_code == 200

    # Read file directly to verify persistence
    file_content = json.loads(mock_inventory_path.read_text())
    assert "persistent_host" in file_content["inventory"]
    assert file_content["inventory"]["persistent_host"]["ansible_user"] == "persist_user"

def test_invalid_inventory_data(client, mock_inventory_path):
    """Test handling of invalid inventory data"""

    # Test with missing required fields
    invalid_host = {
        "id": "invalid_host",
        "ansible_user": "test_user"
        # Missing other required fields
    }

    response = client.post("/ansible/inventory", json=invalid_host)
    assert response.status_code == 422  # Validation error

    # Test with invalid port number
    invalid_port_host = {
        "id": "invalid_port",
        "ansible_user": "test_user",
        "ansible_host": "localhost",
        "ansible_port": -1,  # Invalid port
        "http_proxy": "",
        "https_proxy": "",
        "volttron_venv": "/test/venv",
        "host_configs_dir": "/test/configs"
    }

    response = client.post("/ansible/inventory", json=invalid_port_host)
    assert response.status_code == 422

def test_concurrent_inventory_access(client, mock_inventory_path):
    """Test concurrent access to inventory"""
    import concurrent.futures
    from time import sleep

    def add_host(host_id):
        # Add small delay to increase chance of concurrent access
        sleep(0.1)
        return client.post("/ansible/inventory", json={
            "id": f"concurrent_host_{host_id}",
            "ansible_user": f"user_{host_id}",
            "ansible_host": "localhost",
            "ansible_port": 22,
            "http_proxy": "",
            "https_proxy": "",
            "volttron_venv": f"/venv_{host_id}",
            "host_configs_dir": f"/configs_{host_id}"
        })

    # Add multiple hosts concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(add_host, i) for i in range(5)]
        responses = [f.result() for f in futures]

    # Verify all requests succeeded
    assert all(r.status_code == 200 for r in responses)

    # Verify all hosts were added
    response = client.get("/ansible/inventory")
    final_inventory = response.json()
    assert all(f"concurrent_host_{i}" in final_inventory["inventory"] for i in range(5))

def test_inventory_file_corruption(client, mock_inventory_path):
    """Test handling of corrupted inventory file"""

    # Corrupt the inventory file
    mock_inventory_path.write_text("invalid json content")

    # Attempt to get inventory - should return empty inventory instead of error
    response = client.get("/ansible/inventory")
    assert response.status_code == 200
    assert response.json() == {"inventory": {}}

    # Attempt to add new host
    new_host = {
        "id": "new_host",
        "ansible_user": "test_user",
        "ansible_host": "localhost",
        "ansible_port": 22,
        "http_proxy": "",
        "https_proxy": "",
        "volttron_venv": "/test/venv",
        "host_configs_dir": "/test/configs"
    }

    response = client.post("/ansible/inventory", json=new_host)
    assert response.status_code == 200

    # Verify new inventory was created
    response = client.get("/ansible/inventory")
    assert response.status_code == 200
    inventory = response.json()
    assert "new_host" in inventory["inventory"]
