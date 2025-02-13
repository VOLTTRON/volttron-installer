import pytest
from fastapi.testclient import TestClient
from volttron_installer.backend.endpoints import ansible_router, platform_router, task_router
from fastapi import FastAPI

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(ansible_router)
    app.include_router(platform_router)
    app.include_router(task_router)
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.mark.asyncio
async def test_deploy_platform(client, mocker):
    # Mock the ansible service
    mock_process = mocker.AsyncMock()
    async def mock_run_playbook(*args, **kwargs):
        return (0, "success", "")
    mock_process.run_playbook = mock_run_playbook

    # Fix the mock path to match where ansible_service is instantiated
    mock_ansible = mocker.patch('volttron_installer.backend.endpoints.AnsibleService')
    mock_ansible.return_value = mock_process

    # Test data
    platform_config = {
        "title": "Test Platform",
        "address": "127.0.0.1",
        "bus_type": "zmq",
        "ports": "22916",
        "host": {},
        "agents": {}
    }

    # Make request
    response = client.post("/ansible/ansible/deploy_platform", json=platform_config)

    # Verify response
    assert response.status_code == 200
    assert response.json() == {
        "message": "Platform deployed successfully",
        "output": "success"
    }

@pytest.mark.asyncio
async def test_start_platform(client, mocker):
    # Mock the ansible service
    mock_process = mocker.AsyncMock()
    async def mock_run_ad_hoc(*args, **kwargs):
        return (0, "started", "")
    mock_process.run_ad_hoc = mock_run_ad_hoc

    mock_ansible = mocker.patch('volttron_installer.backend.endpoints.AnsibleService')
    mock_ansible.return_value = mock_process

    # Make request
    response = client.post("/ansible/ansible/start_platform?platform_id=test-platform")

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"message": "Platform started successfully"}

@pytest.mark.asyncio
async def test_stop_platform(client, mocker):
    # Mock the ansible service
    mock_process = mocker.AsyncMock()
    async def mock_run_ad_hoc(*args, **kwargs):
        return (0, "stopped", "")
    mock_process.run_ad_hoc = mock_run_ad_hoc

    mock_ansible = mocker.patch('volttron_installer.backend.endpoints.AnsibleService')
    mock_ansible.return_value = mock_process

    # Make request
    response = client.post("/ansible/ansible/stop_platform?platform_id=test-platform")

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"message": "Platform stopped successfully"}

@pytest.mark.asyncio
async def test_deploy_platform_failure(client, mocker):
    # Mock the ansible service to simulate failure
    mock_process = mocker.AsyncMock()
    async def mock_run_playbook(*args, **kwargs):
        return (1, "", "deployment failed")
    mock_process.run_playbook = mock_run_playbook

    mock_ansible = mocker.patch('volttron_installer.backend.endpoints.AnsibleService')
    mock_ansible.return_value = mock_process

    # Test data
    platform_config = {
        "title": "Test Platform",
        "address": "127.0.0.1"
    }

    # Make request
    response = client.post("/ansible/ansible/deploy_platform", json=platform_config)

    # Verify response
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Ansible deployment failed: deployment failed"
    }
