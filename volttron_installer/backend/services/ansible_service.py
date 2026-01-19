import asyncio
from pathlib import Path
import subprocess
from typing import Optional
from .. models import HostEntry, PlatformDeploymentStatus
from .. services.inventory_service import get_inventory_service, InventoryService
from .. services.platform_service import get_platform_service, PlatformService
import json
import os
from os.path import exists

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

    async def run_ssh_command(self, host: 'HostEntry', command: str, timeout: int = 30) -> tuple[int, str, str]:
        """Run a command via SSH directly (bypassing Ansible for speed).

        Args:
            host: HostEntry with connection details
            command: Command to execute on remote host
            timeout: Timeout in seconds

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            ssh_cmd = [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "BatchMode=yes",
                "-o", f"ConnectTimeout={timeout}",
                "-p", str(host.ansible_port),
                f"{host.ansible_user}@{host.ansible_host}",
                command
            ]

            logger.debug(f"Running SSH command: {' '.join(ssh_cmd)}")

            process = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return -1, "", "SSH command timed out"

            return (
                process.returncode,
                stdout.decode() if stdout else "",
                stderr.decode() if stderr else ""
            )
        except Exception as e:
            logger.error(f"SSH command failed: {e}")
            return -1, "", str(e)
            

    async def run_playbook(self, playbook_name: str, hosts: str | list[str], password: str = None, extra_vars: dict = None, ignore_host_keys: bool = False) -> tuple[int, str, str]:
        """Run an Ansible playbook asynchronously

        Args:
            playbook_name: Name of the playbook (e.g., 'volttron.deployment.install-platform')
            inventory: Ansible inventory string
            connection: Connection type (local, ssh, etc)
            extra_vars: Optional dict of extra variables to pass
            ignore_host_keys: Whether to ignore SSH host key checking

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        inventory_service = await get_inventory_service()
        cmd:str
        output_cmd: str
        pass_holder = "********"
        
        # Build extra vars dictionary
        combined_extra_vars = {}
        if extra_vars:
            combined_extra_vars.update(extra_vars)
            
        if password:
            combined_extra_vars["ansible_become_pass"] = password
            
        if ignore_host_keys:
            combined_extra_vars["ansible_ssh_common_args"] = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
            
        # Create safe version for logging (redact password)
        safe_extra_vars = combined_extra_vars.copy()
        if password:
            safe_extra_vars["ansible_become_pass"] = pass_holder
            
        extra_vars_json = json.dumps(combined_extra_vars)
        safe_extra_vars_json = json.dumps(safe_extra_vars)

        if password == None: 
            cmd = ["ansible-playbook", "-i", inventory_service.inventory_path.as_posix()]
            output_cmd = ["ansible-playbook", "-i", inventory_service.inventory_path.as_posix()]
        else:
            cmd = ["sshpass","-p", password, "ansible-playbook", "-k", "-i", inventory_service.inventory_path.as_posix()]
            output_cmd = ["sshpass","-p", pass_holder, "ansible-playbook", "-k", "-i", inventory_service.inventory_path.as_posix()]

        # Add extra vars
        if combined_extra_vars:
            cmd.extend(["--extra-vars", extra_vars_json])
            output_cmd.extend(["--extra-vars", safe_extra_vars_json])

        if hosts:
            limit_args = ["--limit", ",".join(hosts) if isinstance(hosts, list) else hosts]
            cmd.extend(limit_args)
            output_cmd.extend(limit_args)


        logger.debug(f"Running playbook {playbook_name} on hosts {hosts} cmd: {output_cmd}")
        # if connection:
        #     cmd.extend(["--connection", connection])

        # Merge default vars with provided vars
        # default_vars = {
        #     "ansible_ssh_common_args": "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        # }
        # if extra_vars:
        #     default_vars.update(extra_vars)

        # cmd.extend(["-e", json.dumps(default_vars)])
        # Ensure playbooks are run based on volttron.deployment
        if not playbook_name.startswith('volttron.deployment.'):
            playbook_name = f'volttron.deployment.{playbook_name}'

        # Convert collection path to actual playbook file
        # playbook_file = playbook_name if playbook_name.endswith(".yml") else f"{playbook_name}.yml"
        # cmd.append(str(self.playbook_dir / playbook_file))
        cmd.append(playbook_name)
        output_cmd.append(playbook_name)
        # Set environment variables
        env = os.environ.copy()
        if ignore_host_keys:
            env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
            env['ANSIBLE_SSH_ARGS'] = '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        
        logger.debug(f"Executing command: {' '.join(output_cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        stdout, stderr = await process.communicate()

        logger.debug(f"Playbook output: {stdout.decode() if stdout else stderr.decode()}")
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

        stdout, stderr = await process.communicate(input=b"@Ansible")
        return (
            process.returncode,
            stdout.decode() if stdout else "",
            stderr.decode() if stderr else ""
        )

    async def run_volttron_ad_hoc(self, command: str, hosts: str | list[str], connection: str = "ssh", password: str = None) -> tuple[int, str, str]:
        """Run an ad-hoc Ansible command

        Args:
            command: Command to execute
            hosts: Host(s) to target (instance name from inventory)
            connection: Connection type
            password: Optional password for sudo operations

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        inventory_service = await get_inventory_service()
        
        if password == None:
            cmd = [
                "ansible-playbook", "-i", inventory_service.inventory_path.as_posix(),
                "--connection", connection,
                "volttron.deployment.ad_hoc",
                "-e", f"command='{command}'"
            ]
        else:
            cmd = [
                "sshpass","-p", password, 
                "ansible-playbook","-k", "-i", inventory_service.inventory_path.as_posix(),
                "--connection", connection,
                "volttron.deployment.ad_hoc","-e", f"command='{command}'", "--extra-vars", f'ansible_become_pass="{password}"'
            ]
        
        # Add limit for specific hosts
        if hosts:
            limit_args = ["--limit", ",".join(hosts) if isinstance(hosts, list) else hosts]
            cmd.extend(limit_args)
            
        logger.debug(f"{cmd}")
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

    async def _check_volttron_running(self, instance_name: str, host: 'HostEntry') -> bool:
        """Check if VOLTTRON is running by looking for the process directly via SSH.

        Args:
            instance_name: The instance name from inventory
            host: HostEntry object with connection details

        Returns:
            True if VOLTTRON process is running, False otherwise
        """
        try:
            # Use vctl status to check if VOLTTRON is running - this is the authoritative check
            # vctl returns exit code 0 when running, non-zero when not running
            venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
            volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"

            cmd = f"export VOLTTRON_HOME={volttron_home} && source {venv_path}/bin/activate && vctl status > /dev/null 2>&1 && echo RUNNING || echo STOPPED"

            logger.debug(f"Running vctl status check for {instance_name}")

            return_code, stdout, stderr = await self.run_ssh_command(host, cmd, timeout=15)

            # Log the actual output for debugging
            logger.debug(f"vctl status check for {instance_name}: return_code={return_code}, stdout='{stdout.strip()}'")

            # Check if vctl reported VOLTTRON is running
            is_running = "RUNNING" in stdout and "STOPPED" not in stdout
            logger.debug(f"vctl status result for {instance_name}: is_running={is_running}")
            return is_running
        except Exception as e:
            logger.error(f"Error checking VOLTTRON process for {instance_name}: {e}")
            return False

    async def get_runtime_status(self, instance_name: str, host: 'HostEntry') -> tuple[bool, dict]:
        """Get the actual runtime status of a VOLTTRON instance

        Args:
            instance_name: The instance name from inventory
            host: HostEntry object with connection details

        Returns:
            Tuple of (is_running: bool, agent_status: dict)
        """
        try:
            # Build the vctl status command
            venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
            volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"

            # Command to activate venv and run vctl --json status (using . instead of source for POSIX compatibility)
            cmd = f"export VOLTTRON_HOME={volttron_home} && . {venv_path}/bin/activate && vctl --json status"

            # Execute via ad-hoc command
            logger.info(f"[DEBUG] Running vctl status for {instance_name}")
            return_code, stdout, stderr = await self.run_volttron_ad_hoc(
                command=cmd,
                hosts=instance_name,
                connection=host.ansible_connection
            )
            logger.info(f"[DEBUG] vctl status return_code: {return_code}")
            logger.info(f"[DEBUG] vctl status stdout (first 500 chars): {stdout[:500] if stdout else 'empty'}")

            if return_code != 0:
                logger.warning(f"vctl status failed for {instance_name}: {stderr}")
                logger.debug(f"vctl status stdout: {stdout}")
                # Fallback: check if VOLTTRON process is running
                logger.info(f"[DEBUG] vctl failed, falling back to process check")
                is_running = await self._check_volttron_running(instance_name, host)
                logger.info(f"[DEBUG] Fallback process check result: {is_running}")
                return is_running, {}
            
            # Parse JSON output from vctl status
            import json
            try:
                # Extract JSON from ansible output
                # The output will be in the stdout, look for JSON-like structure
                lines = stdout.split('\n')
                json_data = None
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('{') or line.startswith('['):
                        try:
                            json_data = json.loads(line)
                            break
                        except json.JSONDecodeError:
                            continue
                
                if json_data is None:
                    logger.warning(f"Could not parse vctl status output for {instance_name}")
                    logger.info(f"[DEBUG] No JSON found, falling back to process check")
                    # Fall back to vctl status check
                    is_running = await self._check_volttron_running(instance_name, host)
                    return is_running, {}

                logger.info(f"[DEBUG] Parsed JSON data: {json_data}")

                # vctl status --json returns a dict with agent identities as keys
                # Each agent has status info like "running", "stopped", etc.
                agent_status = {}
                if isinstance(json_data, dict):
                    for agent_id, agent_info in json_data.items():
                        if isinstance(agent_info, dict):
                            # Check if agent has a running status
                            agent_running = agent_info.get('running', False) or agent_info.get('status', '').lower() == 'running'
                            agent_status[agent_id] = {
                                'identity': agent_id,
                                'state': 'started' if agent_running else 'stopped'
                            }

                logger.info(f"[DEBUG] Agent status dict: {agent_status}")

                # If we successfully parsed vctl output, the platform is running
                # (even if there are no agents installed yet)
                is_running = True
                logger.info(f"[DEBUG] is_running from agent_status: {is_running}")

                # If no agents found from vctl, fall back to process check
                if not is_running:
                    logger.info(f"[DEBUG] No agents found, falling back to process check")
                    is_running = await self._check_volttron_running(instance_name, host)
                    logger.info(f"[DEBUG] Process check fallback result: {is_running}")

                logger.info(f"[DEBUG] Final is_running value: {is_running}")
                return is_running, agent_status
                
            except Exception as e:
                logger.error(f"Error parsing vctl status output: {e}")
                # Fall back to vctl status check
                try:
                    is_running = await self._check_volttron_running(instance_name, host)
                    return is_running, {}
                except:
                    return False, {}

        except Exception as e:
            logger.error(f"Error getting runtime status for {instance_name}: {e}")
            # Fall back to vctl status check
            try:
                is_running = await self._check_volttron_running(instance_name, host)
                return is_running, {}
            except:
                return False, {}
    
    async def get_platform_status(self, platform_id: str) -> PlatformDeploymentStatus:
        """Get the status of a platform

        Args:
            platform_id: ID of the platform (instance_name)

        Returns:
            PlatformDeploymentStatus object
        """
        inventory_service = await get_inventory_service()
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)
        
        if platform is None:
            logger.error(f"Platform {platform_id} not found")
            raise Exception(f"Platform {platform_id} not found")

        # Get all hosts and access by instance name (which is the inventory key)
        all_hosts = await inventory_service.get_hosts()
        if platform.config.instance_name not in all_hosts:
            logger.error(f"Host entry for {platform.config.instance_name} not found in inventory")
            raise Exception(f"Host entry for {platform.config.instance_name} not found in inventory")
            
        host = all_hosts[platform.config.instance_name]

        logger.debug(f"Host: {host}")

        # Use the instance name as the host identifier for Ansible
        verify_keys = await self.verify_host_keys(host=platform.config.instance_name,
                                                   user=host.ansible_user,
                                                   port=host.ansible_port)
        

        logger.debug(f"Verify keys: {verify_keys}")
        logger.debug(f"Getting status for platform {platform_id}")
        logger.debug(f"Platform {platform_id} found: {platform}")
        
        keys_verified, _ = verify_keys
        
        # Get actual runtime status
        is_running, agent_statuses = await self.get_runtime_status(
            platform.config.instance_name, 
            host
        )
        
        # Convert agent statuses to AgentStatus objects
        from ..models import AgentStatus
        agents = {
            agent_id: AgentStatus(**status) 
            for agent_id, status in agent_statuses.items()
        }
        
        return PlatformDeploymentStatus(
            platform_id=platform_id,
            host_configured=True,
            keys_verified=keys_verified,
            state="running" if is_running else "deployed",
            agents=agents
        )
    
    async def check_host_connection(self, instance_name: str) -> tuple[bool, str, str]:
        """Quick connection check using Ansible ping module
        
        Args:
            instance_name: The instance name (inventory key) to check
            
        Returns:
            Tuple of (is_connected: bool, connection_method: str, error_message: str)
        """
        try:
            inventory_service = await get_inventory_service()
            all_hosts = await inventory_service.get_hosts()
            
            if instance_name not in all_hosts:
                return False, "", f"Host {instance_name} not found in inventory"
            
            host = all_hosts[instance_name]
            
            # Use ansible ad-hoc ping command for lightweight connection check
            cmd = [
                "ansible",
                instance_name,
                "-i", inventory_service.inventory_path.as_posix(),
                "-m", "ping"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode() if stdout else ""
            stderr_str = stderr.decode() if stderr else ""
            
            if process.returncode == 0 and "SUCCESS" in stdout_str:
                # Determine connection method from host config
                conn_type = host.ansible_connection or "ssh"
                auth_method = "key authentication" if not getattr(host, 'ansible_password', None) else "password"
                connection_method = f"{conn_type.upper()} with {auth_method}"
                return True, connection_method, ""
            else:
                error_msg = stderr_str or stdout_str or "Connection check failed"
                # Only log errors, not successful checks
                logger.warning(f"Connection check failed for {instance_name}: {error_msg}")
                return False, "", error_msg
                
        except Exception as e:
            logger.error(f"Error in check_host_connection: {e}")
            return False, "", str(e)


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
            elif "failed=0" in stdout and ("ok=" in stdout or "changed=" in stdout):
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
        path =os.getenv("VI_DATA_DIR")
        path = os.path.expanduser(path)
        if os.path.exists(path):
            final_path = path +"/inventory.yml"
            with open(final_path, "r") as file:
                data = yaml.safe_load(file)
        # Implement the logic to retrieve the HostEntry by its ID
        # This is a placeholder implementation
            tmp_str = str(data)
            if data['all']['hosts'][host_id]:
                if "ansible_password" in tmp_str:
                    password = data['all']['hosts'][host_id]['ansible_password']
                    return HostEntry(ansible_host=host_id, anisible_user=data['all']['hosts'][host_id]['ansible_user'], port=data['all']['hosts'][host_id]['ansible_port'], password = data['all']['hosts'][host_id]['ansible_password'], ansible_connection = data['all']['hosts'][host_id]['ansible_connection'])
            
                return HostEntry(ansible_host=host_id, ansible_user=data['all']['hosts'][host_id]['ansible_user'], port=data['all']['hosts'][host_id]['ansible_port'], id = data['all']['hosts'][host_id]['ansible_host'], ansible_connection = data['all']['hosts'][host_id]['ansible_connection'])
            else:
                print("HOST IS NOT A MEMBER OF INVENTORY FILE")
                return None
        else:
            print("PATH DOES NOT EXIST TO INVENTORY FILE", path)
            return None

__ansible_service__ = AnsibleService()

async def get_ansible_service() -> AnsibleService:
    return __ansible_service__