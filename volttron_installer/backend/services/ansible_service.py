import asyncio
from pathlib import Path
import subprocess
from typing import Optional
import json
import os

class AnsibleService:
    """Service for executing Ansible playbooks and commands"""

    def __init__(self, playbook_dir: Optional[Path] = None):
        if playbook_dir is None:
            # Use the standard ansible collection path
            # The playbooks are in the root of the collection
            playbook_dir = Path.home() / '.ansible/collections/ansible_collections/volttron/deployment'
        self.playbook_dir = playbook_dir

    async def run_playbook(self, playbook_name: str, inventory: str = "localhost,", connection: str = "local", extra_vars: dict = None) -> tuple[int, str, str]:
        """Run an Ansible playbook asynchronously

        Args:
            playbook_name: Name of the playbook (e.g., 'volttron.deployment.install-platform')
            inventory: Ansible inventory string
            connection: Connection type (local, ssh, etc)
            extra_vars: Optional dict of extra variables to pass

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = ["ansible-playbook", "-i", inventory]

        if connection:
            cmd.extend(["--connection", connection])

        # Merge default vars with provided vars
        default_vars = {
            "ansible_ssh_common_args": "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        }
        if extra_vars:
            default_vars.update(extra_vars)

        cmd.extend(["-e", json.dumps(default_vars)])

        # Handle both full collection paths and direct file paths
        if playbook_name.startswith('volttron.deployment.'):
            # Convert collection path to actual playbook name
            playbook_file = playbook_name.split('.')[-1].replace('_', '-') + '.yml'
            cmd.append(str(self.playbook_dir / playbook_file))
        else:
            # Ensure .yml extension
            if not playbook_name.endswith('.yml'):
                playbook_name += '.yml'
            cmd.append(str(self.playbook_dir / playbook_name))

        # Set environment variables
        env = os.environ.copy()
        env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
        env['ANSIBLE_SSH_ARGS'] = '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        stdout, stderr = await process.communicate()
        return (
            process.returncode,
            stdout.decode() if stdout else "",
            stderr.decode() if stderr else ""
        )

    async def run_ad_hoc(self, command: str, inventory: str = "localhost,", connection: str = "local") -> tuple[int, str, str]:
        """Run an ad-hoc Ansible command

        Args:
            command: Command to execute
            inventory: Ansible inventory string
            connection: Connection type

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = [
            "ansible-playbook", "-i", inventory,
            "--connection", connection,
            "volttron.deployment.ad-hoc",
            "-e", f"command='{command}'"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        return (
            process.returncode,
            stdout.decode() if stdout else "",
            stderr.decode() if stderr else ""
        )

    async def verify_host_keys(self, host: str, user: str, port: int = 22, password: str = None) -> tuple[bool, str]:
        """Verify SSH host keys for a given host

        Args:
            host: Hostname or IP address
            user: Username for SSH connection (typically os.getenv("USER") - the actual system user)
            port: SSH port (default: 22)
            password: Optional SSH password. Should be provided via environment variable,
                     not hardcoded, as it's a security credential.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            host_vars = {
                "ansible_host": host,
                "ansible_user": user,  # System user is safe to use directly
                "ansible_port": port,
                "ansible_connection": "ssh"  # Force SSH connection
            }

            # Only add password if provided - it's a security credential that should come from environment
            if password:
                host_vars["ansible_password"] = password

            return_code, stdout, stderr = await self.run_playbook(
                "ensure-host-keys",
                inventory=f"{host},",  # Use the actual host
                extra_vars=host_vars
            )

            # Check for unreachable hosts or failures
            if "skipping: no hosts matched" in stdout:
                return False, "No matching hosts found"
            elif return_code != 0 or "UNREACHABLE" in stdout:
                return False, f"Host unreachable or verification failed: {stderr or stdout}"
            elif "changed=1" in stdout or "ok=1" in stdout:
                return True, "Host key verification successful"
            else:
                return False, "Unexpected playbook output"

        except Exception as e:
            return False, f"Error during host key verification: {str(e)}"
