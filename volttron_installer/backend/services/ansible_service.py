import asyncio
from pathlib import Path
import subprocess
from typing import Optional

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

        if extra_vars:
            cmd.extend(["-e", f"{extra_vars}"])

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
