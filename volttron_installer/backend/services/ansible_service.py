import asyncio
from pathlib import Path
import subprocess
from typing import Optional
from .. models import HostEntry, PlatformDeploymentStatus
from .. services.inventory_service import get_inventory_service, InventoryService
from .. services.platform_service import get_platform_service, PlatformService
import json
import os

from dotenv import load_dotenv, dotenv_values 
import yaml
from loguru import logger
load_dotenv() 

class AnsibleService:
    """Service for executing Ansible playbooks and commands"""

    def __init__(self, playbook_dir: Optional[Path] = None):
        if playbook_dir is None:
            # Use the standard ansible collection path
            # The playbooks are in the root of the collection
            playbook_dir = Path.home() / '.ansible/collections/ansible_collections/volttron/deployment'
        self.playbook_dir = playbook_dir
            

    async def run_playbook(self, playbook_name: str, hosts: str | list[str], extra_vars: dict = None) -> tuple[int, str, str]:
        """Run an Ansible playbook asynchronously

        Args:
            playbook_name: Name of the playbook (e.g., 'volttron.deployment.install-platform')
            inventory: Ansible inventory string
            connection: Connection type (local, ssh, etc)
            extra_vars: Optional dict of extra variables to pass

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        inventory_service = await get_inventory_service()
        

        cmd = ["ansible-playbook", "-i", inventory_service.inventory_path.as_posix()]

        logger.debug(f"Running playbook {playbook_name} on hosts {hosts} cmd: {cmd}")
        # if connection:
        #     cmd.extend(["--connection", connection])

        # Merge default vars with provided vars
        default_vars = {
            "ansible_ssh_common_args": "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        }
        if extra_vars:
            default_vars.update(extra_vars)

        cmd.extend(["-e", json.dumps(default_vars)])

        # Ensure playbooks are run based on volttron.deployment
        if not playbook_name.startswith('volttron.deployment.'):
            playbook_name = f'volttron.deployment.{playbook_name}'

        # Convert collection path to actual playbook file
        # playbook_file = playbook_name if playbook_name.endswith(".yml") else f"{playbook_name}.yml"
        # cmd.append(str(self.playbook_dir / playbook_file))
        cmd.append(playbook_name)

        
        # Set environment variables
        env = os.environ.copy()
        #env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
        #env['ANSIBLE_SSH_ARGS'] = '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

        logger.debug(f"Executing command: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        stdout, stderr = await process.communicate()
        logger.debug(f"Playbook output: {stdout.decode() if stdout else ''}")
        return (
            process.returncode,
            stdout.decode() if stdout else "",
            stderr.decode() if stderr else ""
        )
    
    async def run_module(self, module_name: str, *args) -> tuple[int, str, str]:
        """Run an Ansible module asynchronously

        Args:
            module_name: Name of the module
            args: Arguments to pass to the module

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        service: InventoryService = await get_inventory_service()

        logger.debug(f"Running module {module_name} with args {args}")
        logger.debug(f"Inventory path: {service.inventory_path}")
        
        cmd = ["ansible", "-i", service.inventory_path.as_posix(), "-m", module_name]

        if args:
            cmd.extend([" ".join(args)])

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

    async def run_volttron_ad_hoc(self, command: str, inventory: str = "localhost,", connection: str = "local") -> tuple[int, str, str]:
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
            "volttron.deployment.ad_hoc",
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
    
    async def get_platform_status(self, platform_id: str) -> PlatformDeploymentStatus:
        """Get the status of a platform

        Args:
            platform_id: ID of the platform

        Returns:
            PlatformDeploymentStatus object
        """
        inventory_service = await get_inventory_service()
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)

        host = await inventory_service.get_host(platform.host_id)

        logger.debug(f"Host: {host}")

        # TODO need to verify the sshpassword is installed.
        verify_keys = await self.verify_host_keys(host=host.id,
                                                   user=host.ansible_user,
                                                   port=host.ansible_port)
        

        logger.debug(f"Verify keys: {verify_keys}")
        logger.debug(f"Getting status for platform {platform_id}")
        if platform is None:
            logger.error(f"Platform {platform_id} not found")
        
        logger.debug(f"Platform {platform_id} found: {platform}")
        

        #await self.verify_host_keys
        
        # return_code, stdout, stderr = await self.run_module("volttron.deployment.get_platform_status", platform_id)
        # if return_code != 0:
        #     raise Exception(f"Error getting platform status: {stderr}")
        
        # return PlatformDeploymentStatus.model_validate(json.loads(stdout))
    


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
                # "ansible_host": host,
                # "ansible_user": user,  # System user is safe to use directly
                # "ansible_port": port,
                "ansible_connection": "ssh"  # Force SSH connection
            }

            # Only add password if provided - it's a security credential that should come from environment
            if password:
                host_vars["ansible_password"] = password

            return_code, stdout, stderr = await self.run_playbook(
                "ensure_host_keys",
                hosts=host,
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

    async def host_config(self, host_entry: HostEntry | str, config_vars: dict = None) -> tuple[int, str, str]:
        """Configure a host using Ansible

        Args:
            host_entry: HostEntry object or string representing the ID of an existing host entry
            config_vars: Optional dict of configuration variables to pass

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        if isinstance(host_entry, str):
            host_entry = await self.get_host_entry_by_id(host_entry)

        host_vars = {
            "ansible_host": host_entry.host,
            "ansible_user": host_entry.user,
            "ansible_port": host_entry.port,
            "ansible_connection": "ssh"
        }

        if host_entry.password:
            host_vars["ansible_password"] = host_entry.password

        if config_vars:
            host_vars.update(config_vars)

        return await self.run_playbook(
            "configure_host",
            hosts=host_entry.id,
            extra_vars=host_vars
        )

    async def get_host_entry_by_id(self, host_id: str) -> 'HostEntry':
        """Retrieve a HostEntry object by its ID

        Args:
            host_id: ID of the host entry

        Returns:
            HostEntry object
        """
        path =  Path.home()/os.getenv("VI_DATA_DIR")
        if os.path.exists(path):
         
            with open(Path.home()/os.getenv("VI_DATA_DIR"), "r") as file:
                data = yaml.safe_load(file)
        # Implement the logic to retrieve the HostEntry by its ID
        # This is a placeholder implementation
            tmp_str = str(data)
            if data['all']['hosts'][host_id]:
                if "ansible_password" in tmp_str:
                    password = data['all']['hosts'][host_id]['ansible_password']
                    return HostEntry(host=host_id, user=data['all']['hosts'][host_id]['ansible_user'], port=data['all']['hosts'][host_id]['ansible_port'], password = data['all']['hosts'][host_id]['ansible_password'])
            
                return HostEntry(host=host_id, user=data['all']['hosts'][host_id]['ansible_user'], port=data['all']['hosts'][host_id]['ansible_port'])
            else:
                print("HOST IS NOT A MEMBER OF INVENTORY FILE")
        else:
            print("PATH DOES NOT EXIST TO INVENTORY FILE")

__ansible_service__ = AnsibleService()

async def get_ansible_service() -> AnsibleService:
    return __ansible_service__