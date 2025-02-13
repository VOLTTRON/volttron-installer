import pytest
from pathlib import Path
from volttron_installer.backend.services.ansible_service import AnsibleService

@pytest.fixture
def ansible_service():
    return AnsibleService(playbook_dir=Path("tests/fixtures/playbooks"))

@pytest.mark.asyncio
async def test_run_playbook(ansible_service, mocker):
    # Mock subprocess
    mock_process = mocker.AsyncMock()
    mock_process.communicate.return_value = (b"success output", b"")
    mock_process.returncode = 0

    mock_subprocess = mocker.patch('asyncio.create_subprocess_exec', return_value=mock_process)

    # Test running a playbook
    return_code, stdout, stderr = await ansible_service.run_playbook(
        "test.yml",
        extra_vars={"test": "value"}
    )

    # Verify subprocess was called correctly
    mock_subprocess.assert_called_once()
    cmd_args = list(mock_subprocess.call_args[0])  # Convert args to list
    assert cmd_args[0] == "ansible-playbook"
    assert cmd_args[1:3] == ["-i", "localhost,"]
    assert cmd_args[3:5] == ["--connection", "local"]
    assert any("-e" in arg for arg in cmd_args)  # Check for extra vars

    # Verify return values
    assert return_code == 0
    assert stdout == "success output"
    assert stderr == ""

@pytest.mark.asyncio
async def test_run_ad_hoc(ansible_service, mocker):
    # Mock subprocess
    mock_process = mocker.AsyncMock()
    mock_process.communicate.return_value = (b"command output", b"")
    mock_process.returncode = 0

    mock_subprocess = mocker.patch('asyncio.create_subprocess_exec', return_value=mock_process)

    # Test running an ad-hoc command
    return_code, stdout, stderr = await ansible_service.run_ad_hoc(
        "test command"
    )

    # Verify subprocess was called correctly
    mock_subprocess.assert_called_once()
    cmd_args = list(mock_subprocess.call_args[0])  # Convert args to list
    assert cmd_args[0] == "ansible-playbook"
    assert "-i" in cmd_args
    assert "localhost," in cmd_args
    assert "-e" in cmd_args
    assert any("command='test command'" in arg for arg in cmd_args)

    # Verify return values
    assert return_code == 0
    assert stdout == "command output"
    assert stderr == ""
