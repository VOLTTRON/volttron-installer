import pytest
from fastapi.testclient import TestClient

from volttron_installer.volttron_installer import app

# This is the location of the fastapi backend.
client = TestClient(app.api)

# Module-level variables for API prefixes
API_PREFIX = "/api"
ANSIBLE_PREFIX = f"{API_PREFIX}/ansible"
PLATFORMS_PREFIX = f"{API_PREFIX}/platforms"
HOSTS_PREFIX = f"{ANSIBLE_PREFIX}/hosts"
CATALOG_PREFIX = f"{API_PREFIX}/catalog"

@pytest.fixture
def create_host_entry():
    client.post(f"{HOSTS_PREFIX}", json={
        "id": "test_host",
        "ansible_user": "user",
        "ansible_host": "127.0.0.1",
        "ansible_port": 22,
        "ansible_connection": "ssh",
        "http_proxy": None,
        "https_proxy": None,
        "volttron_venv": None,
        "volttron_home": "~/.volttron",
        "host_configs_dir": None
    })

def test_create_platform_endpoint(create_host_entry):
    response = client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_get_platform_endpoint(create_host_entry):
    response = client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    assert response.status_code == 200
    assert response.json()["success"] is True
    response = client.get(f"{PLATFORMS_PREFIX}/test_instance")
    assert response.status_code == 200
    assert response.json()["config"]["instance_name"] == "test_instance"

def test_update_platform_endpoint(create_host_entry):
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    response = client.put(f"{PLATFORMS_PREFIX}/test_instance", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22917",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_delete_platform_endpoint(create_host_entry):
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    response = client.delete(f"{PLATFORMS_PREFIX}/test_instance")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_list_platforms_endpoint(create_host_entry):
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "instance1",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "instance2",
            "vip_address": "tcp://127.0.0.1:22917",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    response = client.get(f"{PLATFORMS_PREFIX}/")
    assert response.status_code == 200
    instance_names = [platform["config"]["instance_name"] for platform in response.json()]
    assert "instance1" in instance_names
    assert "instance2" in instance_names

def test_create_agent_in_platform_endpoint(create_host_entry):
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    response = client.post(f"{PLATFORMS_PREFIX}/test_instance/agents", json={
        "identity": "test_agent",
        "source": "some_source"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_remove_agent_from_platform_endpoint(create_host_entry):
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    client.post(f"{PLATFORMS_PREFIX}/test_instance/agents/", json={
        "identity": "test_agent",
        "source": "some_source"
    })
    response = client.delete(f"{PLATFORMS_PREFIX}/test_instance/agents/test_agent")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_update_agent_in_platform_endpoint(create_host_entry):
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    client.post(f"{PLATFORMS_PREFIX}/test_instance/agents", json={
        "identity": "test_agent",
        "source": "some_source"
    })
    response = client.put(f"{PLATFORMS_PREFIX}/test_instance/agents/test_agent", json={
        "identity": "test_agent",
        "source": "updated_source"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_delete_agent_from_platform_endpoint(create_host_entry):
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    client.post(f"{PLATFORMS_PREFIX}/test_instance/agents", json={
        "identity": "test_agent",
        "source": "some_source"
    })
    response = client.delete(f"{PLATFORMS_PREFIX}/test_instance/agents/test_agent")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_create_host_entry():
    response = client.post(f"{HOSTS_PREFIX}", json={
        "id": "test_host",
        "ansible_user": "user",
        "ansible_host": "127.0.0.1",
        "ansible_port": 22,
        "ansible_connection": "ssh",
        "http_proxy": None,
        "https_proxy": None,
        "volttron_venv": None,
        "volttron_home": "~/.volttron",
        "host_configs_dir": None
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_get_host_entry():
    client.post(f"{HOSTS_PREFIX}", json={
        "id": "test_host",
        "ansible_user": "user",
        "ansible_host": "127.0.0.1",
        "ansible_port": 22,
        "ansible_connection": "ssh",
        "http_proxy": None,
        "https_proxy": None,
        "volttron_venv": None,
        "volttron_home": "~/.volttron",
        "host_configs_dir": None
    })
    response = client.get(f"{HOSTS_PREFIX}/test_host")
    assert response.status_code == 200
    assert response.json()["id"] == "test_host"

def test_delete_host_entry():
    client.post(f"{HOSTS_PREFIX}", json={
        "id": "test_host",
        "ansible_user": "user",
        "ansible_host": "127.0.0.1",
        "ansible_port": 22,
        "ansible_connection": "ssh",
        "http_proxy": None,
        "https_proxy": None,
        "volttron_venv": None,
        "volttron_home": "~/.volttron",
        "host_configs_dir": None
    })
    response = client.delete(f"{HOSTS_PREFIX}/test_host")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_list_host_entries():
    client.post(f"{HOSTS_PREFIX}", json={
        "id": "test_host1",
        "ansible_user": "user1",
        "ansible_host": "127.0.0.1",
        "ansible_port": 22,
        "ansible_connection": "ssh",
        "http_proxy": None,
        "https_proxy": None,
        "volttron_venv": None,
        "volttron_home": "~/.volttron",
        "host_configs_dir": None
    })
    client.post(f"{HOSTS_PREFIX}", json={
        "id": "test_host2",
        "ansible_user": "user2",
        "ansible_host": "127.0.0.2",
        "ansible_port": 22,
        "ansible_connection": "ssh",
        "http_proxy": None,
        "https_proxy": None,
        "volttron_venv": None,
        "volttron_home": "~/.volttron",
        "host_configs_dir": None
    })
    response = client.get(f"{HOSTS_PREFIX}")
    assert response.status_code == 200
    host_ids = [host["id"] for host in response.json()]
    assert "test_host1" in host_ids
    assert "test_host2" in host_ids

def test_get_platforms(create_host_entry):
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "instance1",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "instance2",
            "vip_address": "tcp://127.0.0.1:22917",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    response = client.get(f"{PLATFORMS_PREFIX}/")
    assert response.status_code == 200
    platforms = response.json()
    assert len(platforms) >= 2
    instance_names = [platform["config"]["instance_name"] for platform in platforms]
    assert "instance1" in instance_names
    assert "instance2" in instance_names

def test_get_agent_catalog():
    response = client.get(f"{CATALOG_PREFIX}/agents")
    assert response.status_code == 200
    agents = response.json()
    assert "listener" in agents
    assert "platform.driver" in agents

def test_get_agent_from_catalog():
    response = client.get(f"{CATALOG_PREFIX}/agents/listener")
    assert response.status_code == 200
    agent = response.json()
    assert agent["identity"] == "listener"
    assert agent["source"] == "examples/ListenerAgent"

    response = client.get(f"{CATALOG_PREFIX}/agents/platform.driver")
    assert response.status_code == 200
    agent = response.json()
    assert agent["identity"] == "platform.driver"
    assert agent["source"] == "services/core/PlatformDriverAgent"

    response = client.get(f"{CATALOG_PREFIX}/agents/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found in catalog"

def test_get_nonexistent_platform():
    response = client.get(f"{PLATFORMS_PREFIX}/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Platform not found"

def test_get_nonexistent_host():
    response = client.get(f"{HOSTS_PREFIX}/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Host entry not found"

def test_ping_nonexistent_host():
    response = client.get(f"{ANSIBLE_PREFIX}/ping/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Host entry not found"

def test_get_nonexistent_agent_from_catalog():
    response = client.get(f"{CATALOG_PREFIX}/agents/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found in catalog"

def test_create_agent_from_catalog(create_host_entry):
    client.post(f"{PLATFORMS_PREFIX}/", json={
        "host_id": "test_host",
        "config": {
            "instance_name": "test_instance",
            "vip_address": "tcp://127.0.0.1:22916",
            "message_bus": "zmq"
        },
        "agents": {}
    })
    response = client.post(f"{PLATFORMS_PREFIX}/test_instance/agents", json={
        "identity": "listener",
        "source": "examples/ListenerAgent"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

    response = client.get(f"{PLATFORMS_PREFIX}/test_instance")
    assert response.status_code == 200
    platform = response.json()
    assert "listener" in platform["agents"]
