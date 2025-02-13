import pytest
from pathlib import Path
import subprocess
import json
import re

def test_ansible_version():
    """Test that ansible version is >= 2.9"""
    try:
        result = subprocess.run(
            ['ansible', '--version'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "ansible command failed"

        # Parse version from output using regex
        version_match = re.search(r'ansible \[core ([0-9]+\.[0-9]+)', result.stdout)
        assert version_match, "Could not parse ansible version"

        version_str = version_match.group(1)
        major, minor = map(float, version_str.split('.'))
        assert (major, minor) >= (2, 9), f"Ansible version {major}.{minor} is less than required 2.9"

    except FileNotFoundError:
        pytest.fail("ansible command not found. Try: pip3 install ansible")

def test_volttron_ansible_installed():
    """Test that volttron-ansible is installed from GitHub"""
    try:
        # First check if ansible-galaxy is available
        version_result = subprocess.run(
            ['ansible-galaxy', '--version'],
            capture_output=True,
            text=True
        )
        assert version_result.returncode == 0, "ansible-galaxy command failed"

        # Try to install/update volttron-ansible
        install_result = subprocess.run(
            ['ansible-galaxy', 'collection', 'install', '-f', 'git+https://github.com/volttron/volttron-ansible.git'],
            capture_output=True,
            text=True
        )
        assert install_result.returncode == 0, f"Failed to install volttron-ansible: {install_result.stderr}"

    except FileNotFoundError:
        pytest.fail("ansible-galaxy command not found. Try: pip3 install ansible")

def test_ansible_playbooks_available():
    """Test that required Ansible playbooks are available"""
    # Check in the standard ansible collection paths
    collection_paths = [
        Path.home() / '.ansible/collections/ansible_collections/volttron/deployment',
        Path('/usr/share/ansible/collections/ansible_collections/volttron/deployment'),
    ]

    # List of required playbooks with correct names
    required_playbooks = [
        'install-platform.yml',
        'configure-agents.yml',
        'ad-hoc.yml',
        'ensure-host-keys.yml',
        'host-config.yml'
    ]

    playbooks_found = False
    for base_path in collection_paths:
        if base_path.exists():
            playbooks_found = True
            for playbook in required_playbooks:
                playbook_path = base_path / playbook
                assert playbook_path.exists(), f"Playbook {playbook} not found at {playbook_path}"

    if not playbooks_found:
        pytest.fail("No ansible collection paths found. Try running: ansible-galaxy collection install git+https://github.com/volttron/volttron-ansible.git")

def test_ansible_executable():
    """Test that ansible-playbook command is available"""
    try:
        result = subprocess.run(['ansible-playbook', '--version'],
                              capture_output=True,
                              text=True)
        assert result.returncode == 0, "ansible-playbook command failed"
        assert "ansible-playbook" in result.stdout, "ansible-playbook not found in output"
    except FileNotFoundError:
        pytest.fail("ansible-playbook command not found. Try: pip3 install ansible")

def test_ansible_connection():
    """Test that ansible can connect to localhost"""
    try:
        result = subprocess.run(
            ['ansible', 'localhost', '-m', 'ping'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Ansible localhost connection failed"
        assert "SUCCESS" in result.stdout, "Ansible ping to localhost failed"
    except FileNotFoundError:
        pytest.fail("ansible command not found. Try: pip3 install ansible")

@pytest.mark.asyncio
async def test_ansible_service_initialization():
    """Test that AnsibleService can be initialized with default playbook directory"""
    from volttron_installer.backend.services.ansible_service import AnsibleService

    try:
        # Use the actual playbooks path from the installed collection
        collection_path = Path.home() / '.ansible/collections/ansible_collections/volttron/deployment'
        service = AnsibleService(playbook_dir=collection_path)

        # Verify playbook directory exists
        assert service.playbook_dir.exists(), f"Playbook directory not found at {service.playbook_dir}"
        assert service.playbook_dir.is_dir(), f"{service.playbook_dir} is not a directory"

        # Check for required playbooks with correct names
        required_playbooks = [
            'install-platform.yml',
            'configure-agents.yml',
            'ad-hoc.yml',
            'ensure-host-keys.yml',
            'host-config.yml'
        ]
        for playbook in required_playbooks:
            assert (service.playbook_dir / playbook).exists(), f"Required playbook {playbook} not found"

    except Exception as e:
        pytest.fail(f"Failed to initialize AnsibleService: {str(e)}")
