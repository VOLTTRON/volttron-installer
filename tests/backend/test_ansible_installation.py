import pytest
from pathlib import Path
import subprocess
import json
import re
import os
import yaml

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

def check_sshd_available():
    """Check if sshd is installed and running without requiring root privileges"""
    try:
        # Try to connect to localhost SSH port
        result = subprocess.run(
            ['nc', '-z', 'localhost', '22'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True

        # Alternative check using netstat
        result = subprocess.run(
            ['netstat', '-tuln'],
            capture_output=True,
            text=True
        )
        return ':22 ' in result.stdout

    except FileNotFoundError:
        # If neither nc nor netstat is available, try a direct socket connection
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', 22))
            sock.close()
            return result == 0
        except:
            return False

def get_test_password():
    """Get password from environment or skip test if not available.

    Unlike the user (which we get from os.getenv("USER")), the password is a security
    credential that must be provided via environment variable. This allows the tests
    to run both locally and in CI/CD environments without hardcoding credentials.
    """
    password = os.getenv("ANSIBLE_TEST_PASSWORD")
    if not password:
        pytest.skip("ANSIBLE_TEST_PASSWORD environment variable not set")
    return password

@pytest.mark.asyncio
async def test_host_key_verification():
    """Test that we can verify SSH keys for a host using ensure-host-keys playbook"""
    if not check_sshd_available():
        pytest.skip("sshd not available - skipping SSH key verification tests")

    from volttron_installer.backend.services.ansible_service import AnsibleService
    import hashlib
    import base64
    import stat

    try:
        service = AnsibleService()

        # Test data for host verification
        test_host = {
            "ansible_host": "localhost",  # Use localhost for testing
            "ansible_user": os.getenv("USER"),  # Use actual system user - this is safe as it's not a credential
            "ansible_port": 22
        }

        # Ensure .ssh directory exists with proper permissions
        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)

        # Get known_hosts file path
        known_hosts = ssh_dir / "known_hosts"

        # Backup existing known_hosts if it exists
        backup_path = None
        if known_hosts.exists():
            backup_path = known_hosts.parent / "known_hosts.bak"
            known_hosts.rename(backup_path)

        try:
            password = get_test_password()
            # Run the ensure-host-keys playbook
            return_code, stdout, stderr = await service.run_playbook(
                "ensure-host-keys",
                inventory="localhost,",
                extra_vars={
                    "ansible_host": test_host["ansible_host"],
                    "ansible_user": test_host["ansible_user"],
                    "ansible_port": test_host["ansible_port"],
                    "ansible_connection": "local",
                    "ansible_password": password,
                    "ansible_ssh_common_args": "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
                }
            )

            # Check results
            assert return_code == 0, f"Host key verification failed: {stderr}"
            assert "FAILED" not in stdout, f"Playbook reported failure: {stdout}"

            # Verify known_hosts file exists
            assert known_hosts.exists(), "known_hosts file not created"

            # Verify file permissions
            assert known_hosts.stat().st_mode & 0o777 == 0o644, "known_hosts has incorrect permissions"

            # Verify the playbook reported success
            assert "changed=1" in stdout or "ok=1" in stdout, \
                "Playbook did not report successful key verification"

            # Verify file contains new content
            assert known_hosts.stat().st_size > 0, "known_hosts file is empty"

        finally:
            # Restore original known_hosts file
            if backup_path and backup_path.exists():
                if known_hosts.exists():
                    known_hosts.unlink()
                backup_path.rename(known_hosts)

    except Exception as e:
        pytest.fail(f"Host key verification failed: {str(e)}")

@pytest.mark.asyncio
async def test_host_key_verification_with_invalid_host():
    """Test that host key verification fails appropriately with invalid host"""
    from volttron_installer.backend.services.ansible_service import AnsibleService

    try:
        service = AnsibleService()

        # Test data with invalid host
        test_host = {
            "ansible_host": "invalid.host.local",  # Non-existent host
            "ansible_user": "invalid_user",
            "ansible_port": 22
        }

        # Ensure .ssh directory exists
        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)

        # Get known_hosts file path
        known_hosts = ssh_dir / "known_hosts"

        # Backup existing known_hosts if it exists
        backup_path = None
        if known_hosts.exists():
            backup_path = known_hosts.parent / "known_hosts.bak"
            known_hosts.rename(backup_path)

        try:
            # Run the playbook directly to check output
            return_code, stdout, stderr = await service.run_playbook(
                "ensure-host-keys",
                inventory=f"{test_host['ansible_host']},",  # Use specific host
                extra_vars={
                    "ansible_host": test_host["ansible_host"],
                    "ansible_user": test_host["ansible_user"],
                    "ansible_port": test_host["ansible_port"],
                    "ansible_connection": "ssh"
                }
            )

            # Should fail with no hosts matched or unreachable
            assert (return_code != 0) or \
                   ("UNREACHABLE" in stdout) or \
                   ("skipping: no hosts matched" in stdout), \
                "Expected playbook to fail, be unreachable, or have no matching hosts"

        finally:
            # Restore original known_hosts file
            if backup_path and backup_path.exists():
                if known_hosts.exists():
                    known_hosts.unlink()
                backup_path.rename(known_hosts)

    except Exception as e:
        pytest.fail(f"Test failed unexpectedly: {str(e)}")

@pytest.mark.asyncio
async def test_host_key_verification_scenarios():
    """Test host key verification with different host scenarios"""
    if not check_sshd_available():
        pytest.skip("sshd not available - skipping SSH key verification tests")

    password = get_test_password()
    from volttron_installer.backend.services.ansible_service import AnsibleService
    import stat

    test_scenarios = [
        {
            "name": "localhost_ip",
            "host": "127.0.0.1",
            "expected_success": True
        },
        {
            "name": "localhost_name",
            "host": "localhost",
            "expected_success": True
        },
        {
            "name": "remote_ip",
            "host": "192.168.1.100",  # Example remote IP
            "expected_success": False  # Should fail if host not reachable
        },
        {
            "name": "hostname",
            "host": "example.host.com",  # Example hostname
            "expected_success": False  # Should fail if host not resolvable
        }
    ]

    service = AnsibleService()
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    known_hosts = ssh_dir / "known_hosts"

    # Backup existing known_hosts
    backup_path = None
    if known_hosts.exists():
        backup_path = known_hosts.parent / "known_hosts.bak"
        known_hosts.rename(backup_path)

    try:
        for scenario in test_scenarios:
            # Clear known_hosts for each test
            if known_hosts.exists():
                known_hosts.unlink()

            test_host = {
                "ansible_host": scenario["host"],
                "ansible_user": os.getenv("USER"),
                "ansible_port": 22
            }

            return_code, stdout, stderr = await service.run_playbook(
                "ensure-host-keys",
                inventory=f"{scenario['host']},",  # Use specific host
                extra_vars={
                    "ansible_host": test_host["ansible_host"],
                    "ansible_user": test_host["ansible_user"],
                    "ansible_port": test_host["ansible_port"],
                    "ansible_password": password,  # Use password from environment
                    "ansible_connection": "local" if scenario["host"] in ["localhost", "127.0.0.1"] else "ssh"
                }
            )

            if scenario["expected_success"]:
                assert return_code == 0, \
                    f"Host key verification failed for {scenario['name']}: {stderr}"
                assert known_hosts.exists(), \
                    f"known_hosts file not created for {scenario['name']}"
                assert known_hosts.stat().st_mode & 0o777 == 0o644, \
                    f"known_hosts has incorrect permissions for {scenario['name']}"
                assert known_hosts.stat().st_size > 0, \
                    f"known_hosts is empty for {scenario['name']}"
            else:
                assert return_code != 0 or "UNREACHABLE" in stdout, \
                    f"Expected failure for {scenario['name']} but got success"

    finally:
        # Restore original known_hosts
        if known_hosts.exists():
            known_hosts.unlink()
        if backup_path and backup_path.exists():
            backup_path.rename(known_hosts)

@pytest.mark.asyncio
async def test_host_key_verification_with_ssh_options():
    """Test host key verification with different SSH options"""
    if not check_sshd_available():
        pytest.skip("sshd not available - skipping SSH key verification tests")

    password = get_test_password()
    from volttron_installer.backend.services.ansible_service import AnsibleService

    test_cases = [
        {
            "name": "custom_port",
            "host": "localhost",
            "port": 2222,  # Non-standard port
            "expected_success": False  # Should fail if port not open
        },
        {
            "name": "different_user",
            "host": "localhost",
            "user": "nonexistent_user",
            "expected_success": False  # Should fail with invalid user
        },
        {
            "name": "standard_setup",
            "host": "localhost",
            "user": os.getenv("USER"),
            "port": 22,
            "expected_success": True
        }
    ]

    service = AnsibleService()
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    known_hosts = ssh_dir / "known_hosts"

    # Backup existing known_hosts
    backup_path = None
    if known_hosts.exists():
        backup_path = known_hosts.parent / "known_hosts.bak"
        known_hosts.rename(backup_path)

    try:
        for case in test_cases:
            if known_hosts.exists():
                known_hosts.unlink()

            success, message = await service.verify_host_keys(
                host=case["host"],
                user=case.get("user", os.getenv("USER")),
                port=case.get("port", 22),
                password=password  # Add password parameter
            )

            assert success == case["expected_success"], \
                f"Test case {case['name']}: expected success={case['expected_success']}, got {success}. Message: {message}"

    finally:
        if known_hosts.exists():
            known_hosts.unlink()
        if backup_path and backup_path.exists():
            backup_path.rename(known_hosts)

@pytest.mark.asyncio
async def test_host_location_given_host_id():
    test_pass_existence = False
    #gets a known test case 
    with open(Path.home() /'.volttron_installer_data/inventory.yml', 'r') as file:
        data = yaml.safe_load(file)
        
    host_id = 'test_host' #set existing host id
    temp_string = str(data)
    
    assert host_id in temp_string
    
    if host_id in temp_string:
        user=data['all']['hosts'][host_id]['ansible_user']
        port=data['all']['hosts'][host_id]['ansible_port']
    
    if 'ansible_password' in temp_string:
        test_pass_existence = True
        
    assert test_pass_existence == False
    assert user == "user"#is proper information from test_host
    assert port == 22
