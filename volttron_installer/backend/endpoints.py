from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Any, Optional
from ..utils import get_api_url
import os, asyncio, shlex
from loguru import logger

from volttron_installer.backend.tool_manager import ToolManager
from volttron_installer.backend.services.ansible_service import AnsibleService, get_ansible_service
from volttron_installer.backend.services.inventory_service import InventoryService, get_inventory_service
from volttron_installer.backend.services.platform_service import PlatformService, get_platform_service
from volttron_installer.backend.models import AgentCatalog

from volttron_installer.backend.tool_proxy_factory import ToolProxyFactory

from bacnet_scan_api.models import ScanResponse, ObjectListNamesResponse

from .models import (
    CreateOrUpdateHostEntryRequest,
    SuccessResponse,
    CreatePlatformRequest,
    PlatformDefinition,
    HostEntry,
    PlatformConfig,
    AgentType,
    AgentCatalog,
    CreateAgentRequest,
    AgentDefinition,
    DeployPlatformRequest,
    PlatformDeplymentStatusRequest,
    ReachableResponse,
    ToolRequest,
    ToolStatusResponse,
    BACnetDevice,
    BACnetReadPropertyRequest,
    BACnetScanResults,
    BACnetWritePropertyRequest,
    BACnetReadDeviceAllRequest
)

TOOLS_PREFIX = "/tools"

platform_router = APIRouter(prefix="/platforms", tags=["platforms"])
ansible_router = APIRouter(prefix="/ansible", tags=["ansible"])
task_router = APIRouter(prefix="/task", tags=["tasks"])
catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])
tool_management_router = APIRouter(prefix="/manage_tools", tags=["manage tools"])
bacnet_scan_api_router = APIRouter(prefix=f"{TOOLS_PREFIX}/bacnet_scan_api", tags=["bacnet scan tool"])

@ansible_router.get("/hosts", response_model=list[HostEntry])
async def get_hosts() -> list[HostEntry]:
    """Retrieves a list of `HostEntry` items"""
    try:
        inventory_service = await get_inventory_service()
        hosts = await inventory_service.get_hosts()
        return list(hosts.values())
    except Exception as e:
        # Return empty inventory on any error
        return []

@ansible_router.get("/hosts/{id}", response_model=HostEntry)
async def get_host_id(id: str) -> HostEntry | None:
    """Retrieves a host entry by its ID"""
    try:
        inventory_service = await get_inventory_service()
        host_entry = await inventory_service.get_host(id)
        if host_entry is None:
            raise HTTPException(status_code=404, detail="Host entry not found")
        return host_entry
    except HTTPException as e:
        raise e
    except Exception as e:  
        # Return empty inventory on any error
        return None

@ansible_router.post("/hosts")
async def add_host(host_entry: CreateOrUpdateHostEntryRequest):
    """Adds a new host entry to the inventory"""
    try:
        # Create HostEntry first to validate
        item = HostEntry(
            id=host_entry.id,
            ansible_user=host_entry.ansible_user,
            ansible_host=host_entry.ansible_host,
            ansible_port=host_entry.ansible_port,
            http_proxy=host_entry.http_proxy,
            https_proxy=host_entry.https_proxy,
            volttron_venv=host_entry.volttron_venv,
            host_configs_dir=host_entry.host_configs_dir,
            instance_name=host_entry.instance_name
        )

        inventory_service = await get_inventory_service()
        await inventory_service.create_host(item)
        return SuccessResponse()

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@ansible_router.delete("/hosts/{id}")
async def remove_from_inventory(id: str):
    """Removes a host entry from the inventory"""
    try:
        inventory_service = await get_inventory_service()
        await inventory_service.remove_host(id)
        return SuccessResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@platform_router.get("/")
async def get_all_platforms() -> list[PlatformDefinition]:
    """Retrieves all platforms"""
    try:
        platform_service = await get_platform_service()
        platforms = await platform_service.get_all_platforms()
        return platforms
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"platforms": []}

@platform_router.get("/{id}")
async def get_platform_by_id(id: str) -> Optional[PlatformDefinition]:
    """Retrieves a specific platform by its ID"""
    try:
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(id)
        if platform is None:
            raise HTTPException(status_code=404, detail="Platform not found")
        return platform
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@platform_router.post("/")
async def create_platform(platform: CreatePlatformRequest,
                          inventory_service: InventoryService = Depends(get_inventory_service),
                          platform_service: PlatformService = Depends(get_platform_service)) -> SuccessResponse:
    """Creates a new platform"""
    try:
        host = await inventory_service.get_host(platform.host_id)

        if host is None:
            raise HTTPException(status_code=404, detail="Host not found")
        
        platform_definition = PlatformDefinition(host_id=platform.host_id,
                                                 config=platform.config,
                                                 agents=platform.agents)
        await platform_service.create_platform(platform_definition)
        ans = await get_ansible_service() 
        #await ans.run_playbook("run_platforms",  platform.host_id)
        return SuccessResponse(object=platform_definition)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@platform_router.put("/{id}")
async def update_platform(id: str, platform: CreatePlatformRequest):
    """Updates an existing platform"""
    try:
        platform_service = await get_platform_service()
        platform_definition = PlatformDefinition(host_id=platform.host_id,
                                                 config=platform.config,
                                                 agents=platform.agents)
        await platform_service.update_platform(id, platform_definition)
        return SuccessResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@platform_router.delete("/{id}")
async def delete_platform(id: str):
    """Deletes a platform"""
    try:
        platform_service = await get_platform_service()
        await platform_service.delete_platform(id)
        return SuccessResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@platform_router.get("/status/{platform_id}")
async def get_platform_status(
        platform_id: str,
        ansible_service: AnsibleService = Depends(get_ansible_service),
        platform_service: PlatformService = Depends(get_platform_service)):
    """Retrieves the status of a specific platform"""
    status = await ansible_service.get_platform_status(platform_id)

    if status is None:
        raise HTTPException(status_code=404, detail="Platform not found")
    return status

@platform_router.get("/connection/{platform_id}")
async def check_platform_connection(
        platform_id: str,
        ansible_service: AnsibleService = Depends(get_ansible_service)):
    """Quick connection check for a platform"""
    is_connected, connection_method, error = await ansible_service.check_host_connection(platform_id)

    return {
        "connected": is_connected,
        "connection_method": connection_method,
        "error": error
    }

@platform_router.post("/mark-deployed/{platform_id}")
async def mark_platform_deployed(
        platform_id: str,
        deployed: bool = True,
        platform_service: PlatformService = Depends(get_platform_service)):
    """Mark a platform as deployed (or not deployed) without running deployment.

    Useful for existing platforms that were deployed before the deployed flag was persisted.
    """
    platform = await platform_service.get_platform(platform_id)
    if platform is None:
        raise HTTPException(status_code=404, detail="Platform not found")

    platform.deployed = deployed
    await platform_service.update_platform(platform_id, platform)

    return {"status": "success", "deployed": deployed}

# @ansible_router.get("/update-all-status")
# async def update_all_status():
#     """Updates the status of all platforms"""
#     try:
#         ansible_service = await get_ansible_service()


# @platform_router.post("/deploy")
# async def deploy_platform(deploy):
#     """Deploys a platform"""
#     # Get the platform definition
#     # Deploy the platform
#     return SuccessResponse()

# async def deploy_platforms():
#     """Deploy all the platforms"""
#     return SuccessResponse()

# @platform_router.post("/{id}/run")
# async def run_platform(id: str):
#     """Runs a specific platform"""
#     # TODO: Implement this
#     # ansible-playbook -i <path/to/your/inventory>.yml \
#     #              volttron.deployment.run_platforms
#     return SuccessResponse()

# @platform_router.post("/run")
# async def run_platforms():
#     """Runs all platforms"""
#     return SuccessResponse()

# @platform_router.post("/{id}/configure_agents")
# async def configure_agents(id: str):
#     """Configures agents for a platform"""
#     # Get the platform definition
#     # Configure the agents
#     return SuccessResponse()

# @platform_router.get("/status")
# async def get_platforms_status():
#     """Retrieves the status of all platforms"""
#     return {"status": "ok"}

# @platform_router.get("/{id}/status")
# async def get_platform_status(id: str):
#     """Retrieves the status of a specific platform"""
#     return {"status": "ok"}

# @platform_router.get("/{id}/agents")
# async def get_agents_running_state(id: str):
#     """Retrieves the running state of agents for a platform"""
#     # ansible-playbook -i <path/to/your/inventory>.yml \
#     #             volttron.deployment.ad_hoc -e "command='vctl status'"
#     return {"agents": []}

@platform_router.post("/{platform_id}/agents")
async def create_agent(platform_id: str, agent: CreateAgentRequest):
    """Creates a new agent for a platform"""
    try:
        platform_service = await get_platform_service()
        agent_definition = AgentDefinition(identity=agent.identity,
                                           source=agent.source,
                                           pypi_package=agent.pypi_package,
                                           config_store=agent.config_store)
        await platform_service.create_agent(platform_id, agent_definition)
        return SuccessResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@platform_router.put("/{platform_id}/agents/{agent_id}")
async def update_agent(platform_id: str, agent_id: str, agent: CreateAgentRequest):
    """Updates an existing agent for a platform"""
    try:
        platform_service = await get_platform_service()
        agent_definition = AgentDefinition(**agent.model_dump())
        await platform_service.update_agent(platform_id, agent_id, agent_definition)
        return SuccessResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@platform_router.delete("/{platform_id}/agents/{agent_id}")
async def delete_agent(platform_id: str, agent_id: str):
    """Deletes an agent from a platform"""
    try:
        platform_service = await get_platform_service()
        await platform_service.delete_agent(platform_id, agent_id)
        return SuccessResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@task_router.get("/ping/{host_id}", response_model=ReachableResponse)
async def ping_resolvable_host(host_id: str):
    """
    Pings a specific host and returns if it's reachable
    
    Returns:
        ReachableResponse: Object containing a boolean 'reachable' field
    """
    try:
        # Run ping with a short timeout for faster response
        process = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", host_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        # If returncode is 0, the host is reachable
        return {"reachable": process.returncode == 0}
        
    except Exception:
        # Any error means the host is not reachable
        return {"reachable": False}

@task_router.get("/")
async def get_tasks():
    """Retrieves the list of tasks"""
    # Get the list of tasks
    return {"tasks": []}

@task_router.get("/{id}")
async def task_status(id: str):
    """Retrieves the status of a specific task"""
    # Get the status of the task
    return {"status": "ok"}

@platform_router.post("/deploy/{platform_id}")
async def deploy_platform(platform_id: str, password:str,
                          ansible: AnsibleService = Depends(get_ansible_service),
                          platform_service: PlatformService = Depends(get_platform_service),
                          inventory_service: InventoryService = Depends(get_inventory_service)):

    """Deploys a platform using Ansible"""
    try:
        # platform_service = await get_platform_service() # Removed redundant call
        platform = await platform_service.get_platform(platform_id)
        if platform is None:
            raise HTTPException(status_code=404, detail="Platform not found")
        
        # Check if we should ignore host keys
        # The inventory is keyed by instance name, not host_id
        ignore_host_keys = False
        all_hosts = await inventory_service.get_hosts()
        if platform.config.instance_name in all_hosts:
            ignore_host_keys = all_hosts[platform.config.instance_name].ignore_host_keys

        # Target the platform instance name in the inventory
        target_host = platform.config.instance_name

        ret, stdout, stderr = await ansible.run_playbook("host_config", target_host, password, ignore_host_keys=ignore_host_keys)

        if ret != 0:
            error_message = _parse_ansible_error(ret, stdout, stderr)
            raise HTTPException(
                status_code=500,
                detail=f"Host configuration failed: {error_message}"
            )

        return_code, stdout, stderr = await ansible.run_playbook(
            "install_platform",
            target_host,
            password,
            extra_vars=platform.config.model_dump(),
            ignore_host_keys=ignore_host_keys
        )

        if return_code != 0:
            error_message = _parse_ansible_error(return_code, stdout, stderr)
            raise HTTPException(
                status_code=500,
                detail=f"Platform installation failed: {error_message}"
            )
        
        # Clean up config file - remove duplicate snake_case fields and installer-only fields that VOLTTRON doesn't recognize
        # Keep only hyphenated versions: instance-name, message-bus, vip-address
        # Remove volttron_type (installer-only field)
        cleanup_cmd = "sed -i '/^instance_name =/d; /^messagebus =/d; /^message_bus =/d; /^options =/d; /^vip_address =/d; /^volttron_type =/d' ~/.volttron/config"
        await ansible.run_volttron_ad_hoc(
            command=cleanup_cmd,
            hosts=platform.config.instance_name,
            connection="ssh"
        )

        # Mark platform as deployed and save to file
        platform.deployed = True
        await platform_service.update_platform(platform.config.instance_name, platform)

        all_output = stdout
        all_stderr = stderr
        all_tasks = _parse_ansible_tasks(stdout)

        # If there are agents configured, run configure_agents playbook to install them
        if platform.agents:
            logger.info(f"Installing {len(platform.agents)} configured agents for platform {platform_id}")

            agent_return_code, agent_stdout, agent_stderr = await ansible.run_playbook(
                "configure_agents",
                target_host,
                password,
                ignore_host_keys=ignore_host_keys
            )

            all_output += "\n\n=== Agent Configuration ===\n" + agent_stdout
            all_stderr += agent_stderr
            all_tasks.extend(_parse_ansible_tasks(agent_stdout))

            if agent_return_code != 0:
                logger.warning(f"Agent configuration had issues: {agent_stderr}")
                # Don't fail the whole deployment, just warn
                all_output += f"\nWarning: Some agents may not have installed correctly"

        # Return full output including both stdout and stderr
        return {
            "status": "success",
            "output": all_output,
            "stderr": all_stderr,
            "tasks": all_tasks
        }
    

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

def _parse_ansible_tasks(ansible_output: str) -> list[str]:
    """Parse Ansible output to extract task names"""
    tasks = []
    for line in ansible_output.split('\n'):
        if line.startswith('TASK ['):
            # Extract task name from "TASK [task name] ***"
            task_name = line[6:line.rfind(']')].strip()
            tasks.append(task_name)
    return tasks

def _parse_ansible_error(return_code: int, stdout: str, stderr: str) -> str:
    """Parse Ansible output to provide a user-friendly error message.

    Analyzes both stdout and stderr to identify common failure patterns
    and returns a clear, actionable error message.
    """
    import re

    # First, look for specific error messages in fatal/FAILED lines (most reliable)
    # These lines contain the actual error from Ansible
    for line in stdout.split('\n'):
        line_lower = line.lower()
        if 'fatal:' in line_lower or 'failed!' in line_lower:
            # Check for specific errors in the fatal line
            if "incorrect sudo password" in line_lower:
                return "Authentication failed: The sudo password is incorrect."
            if "authentication failure" in line_lower:
                return "Authentication failed: The password is incorrect."
            if "permission denied" in line_lower:
                return "Authentication failed: The password is incorrect or the user doesn't have access."
            if "host key verification failed" in line_lower:
                return "SSH host key verification failed. Try enabling 'Disable Host Key Checking' in the connection settings."
            if "sudo: a password is required" in line_lower or "missing sudo password" in line_lower:
                return "Sudo password required: The remote user needs sudo privileges. Ensure the password is correct."
            if "not in the sudoers file" in line_lower:
                return "Permission denied: The remote user is not in the sudoers file and cannot run privileged commands."
            if "connection refused" in line_lower:
                return "Connection refused: The SSH service may not be running on the remote host, or the port may be blocked."
            if "timed out" in line_lower:
                return "Connection timed out: The host is not responding. Check network connectivity and firewall settings."
            if "name or service not known" in line_lower or "could not resolve" in line_lower:
                return "DNS resolution failed: The hostname could not be resolved. Check the hostname or use an IP address instead."
            if "command not found" in line_lower:
                return "Missing dependency: A required command was not found on the remote host."
            if "no python interpreter found" in line_lower:
                return "Python not found: No Python interpreter found on the remote host. Ensure Python is installed."
            # Check for UNREACHABLE in the fatal line itself (not in PLAY RECAP)
            if "unreachable!" in line_lower:
                return "Host unreachable: Unable to connect to the remote host. Check that the host is online and the IP/hostname is correct."

            # Extract the error message from the JSON-like output if present
            msg_match = re.search(r'"msg":\s*"([^"]+)"', line)
            if msg_match:
                return f"Deployment failed: {msg_match.group(1)}"

            # Return a truncated version of the fatal line
            return f"Deployment failed: {line.strip()[:300]}"

    # Check PLAY RECAP for unreachable hosts (unreachable > 0)
    for line in stdout.split('\n'):
        if 'unreachable=' in line.lower():
            match = re.search(r'unreachable=(\d+)', line.lower())
            if match and int(match.group(1)) > 0:
                return "Host unreachable: Unable to connect to the remote host. Check that the host is online and the IP/hostname is correct."

    # Filter out warnings from stderr to find real errors
    real_errors = []
    for line in stderr.split('\n'):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith('[WARNING]'):
            real_errors.append(line_stripped)

    # If we found real errors in stderr, use those
    if real_errors:
        return f"Deployment failed: {' '.join(real_errors[:3])}"

    # Generic fallback - include both outputs for debugging
    error_detail = stderr.strip() if stderr.strip() else stdout.strip()
    if len(error_detail) > 500:
        error_detail = error_detail[:500] + "..."
    return f"Deployment failed (exit code {return_code}): {error_detail}"
    
# async def deploy_platform(config: PlatformConfig, ansible: AnsibleService = Depends(get_ansible_service)):
#     """Deploys a platform using Ansible"""
#     try:
#         return_code, stdout, stderr = await ansible.run_playbook(
#             "install-platform",  # Updated playbook name
#             extra_vars=config.model_dump()
#         )

#         if return_code != 0:
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"Ansible deployment failed: {stderr or stdout}"
#             )
#         return {"status": "success", "output": stdout}

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )

@ansible_router.post("/start_platform/{platform_id}")
async def start_platform(platform_id: str, ansible: AnsibleService = Depends(get_ansible_service)):
    """Starts a VOLTTRON platform using vctl"""
    try:
        # Get platform definition and host entry
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)
        
        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")
        
        # Get host entry from inventory
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()
        
        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )
        
        host = all_hosts[platform.config.instance_name]

        # Build paths
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"

        # First check if VOLTTRON is already running using vctl status (authoritative check)
        check_cmd = f"export VOLTTRON_HOME={volttron_home} && source {venv_path}/bin/activate && vctl status > /dev/null 2>&1 && echo RUNNING || echo STOPPED"
        check_code, check_stdout, _ = await ansible.run_ssh_command(host, check_cmd, timeout=15)

        if "RUNNING" in check_stdout and "STOPPED" not in check_stdout:
            return {"status": "success", "message": "VOLTTRON is already running.", "already_running": True}

        # Clean up config file - remove snake_case options and installer-only fields that VOLTTRON doesn't recognize
        # Remove: instance_name, messagebus, message_bus, options, vip_address, volttron_type (installer-only)
        # Use direct SSH for speed and reliability
        cleanup_cmd = f"sed -i '/instance_name/d; /messagebus/d; /message_bus/d; /^options/d; /vip_address/d; /volttron_type/d' {volttron_home}/config 2>/dev/null || true"
        await ansible.run_ssh_command(host, cleanup_cmd, timeout=10)

        # Capture stderr/stdout to log file directly (VOLTTRON 2.0's -l flag is broken)
        # Use >> to append, 2>&1 redirects stderr to stdout so both go to log
        # Use direct SSH for speed and reliability
        # Important: redirect stdin from /dev/null and use subshell to properly detach via SSH
        cmd = f"(export VOLTTRON_HOME={volttron_home} && . {venv_path}/bin/activate && nohup volttron -vv >> {volttron_home}/volttron.log 2>&1 &) </dev/null >/dev/null 2>&1"

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=10)

        # nohup with & returns immediately, so return_code 0 just means the command was sent
        # VOLTTRON can take a while to start up (especially first time with dependency installation)
        # Retry checking status for up to 30 seconds
        import asyncio
        max_attempts = 10
        is_running = False

        for attempt in range(max_attempts):
            await asyncio.sleep(3)  # Wait 3 seconds between checks
            is_running = await ansible._check_volttron_running(platform.config.instance_name, host)
            if is_running:
                break
            logger.debug(f"VOLTTRON not ready yet, attempt {attempt + 1}/{max_attempts}")

        if not is_running:
            raise HTTPException(
                status_code=500,
                detail=f"VOLTTRON did not start within 30 seconds. Check logs at {volttron_home}/volttron.log"
            )

        return {"status": "success", "message": "Platform started successfully."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@ansible_router.post("/stop_platform/{platform_id}")
async def stop_platform(platform_id: str, ansible: AnsibleService = Depends(get_ansible_service)):
    """Stops a VOLTTRON platform using vctl"""
    try:
        # Get platform definition and host entry
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)
        
        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")
        
        # Get host entry from inventory
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()
        
        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )
        
        host = all_hosts[platform.config.instance_name]

        # Build paths
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"

        # Use direct SSH for speed and reliability
        cmd = f"export VOLTTRON_HOME={volttron_home} && source {venv_path}/bin/activate && vctl shutdown --platform"

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)

        # vctl shutdown returns 0 on success
        # Give it a moment to shut down, then verify
        import asyncio
        await asyncio.sleep(2)

        # Verify it actually stopped
        is_running = await ansible._check_volttron_running(platform.config.instance_name, host)
        if is_running:
            raise HTTPException(
                status_code=500,
                detail=f"Platform did not stop properly. Try again or check logs at {volttron_home}/volttron.log"
            )

        return {"status": "success", "message": "Platform stopped successfully."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@ansible_router.delete("/delete_remote_files/{platform_id}")
async def delete_remote_volttron_files(platform_id: str, ansible: AnsibleService = Depends(get_ansible_service)):
    """Delete VOLTTRON files on the remote system.

    This will:
    1. Stop VOLTTRON if running
    2. Delete the VOLTTRON_HOME directory
    3. Optionally delete the virtual environment
    """
    try:
        # Get platform definition and host entry
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)

        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

        # Get host entry from inventory
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()

        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )

        host = all_hosts[platform.config.instance_name]

        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"

        # Step 1: Stop VOLTTRON if running (using pkill to ensure it stops)
        stop_cmd = "pkill -f 'volttron -' 2>/dev/null || true"
        await ansible.run_ssh_command(host, stop_cmd, timeout=15)

        # Give it a moment to shut down
        import asyncio
        await asyncio.sleep(2)

        # Step 2: Delete VOLTTRON_HOME directory
        delete_home_cmd = f"rm -rf {volttron_home}"
        return_code, stdout, stderr = await ansible.run_ssh_command(host, delete_home_cmd, timeout=60)

        if return_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete VOLTTRON_HOME: {stderr}"
            )

        # Step 3: Delete virtual environment
        delete_venv_cmd = f"rm -rf {venv_path}"
        return_code, stdout, stderr = await ansible.run_ssh_command(host, delete_venv_cmd, timeout=60)

        if return_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete virtual environment: {stderr}"
            )

        return {
            "status": "success",
            "message": f"Deleted VOLTTRON files: {volttron_home} and {venv_path}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@ansible_router.post("/start_agent/{platform_id}/{agent_id}")
async def start_agent(platform_id: str, agent_id: str, ansible: AnsibleService = Depends(get_ansible_service)):
    """Starts a specific agent on a VOLTTRON platform using vctl"""
    try:
        # Get platform definition and host entry
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)
        
        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")
        
        # Get host entry from inventory
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()
        
        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )
        
        host = all_hosts[platform.config.instance_name]
        
        # Build command to start the agent
        venv_path = host.volttron_venv if host.volttron_venv else "~/.local"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"
        
        cmd = f"export VOLTTRON_HOME={volttron_home} && source {venv_path}/bin/activate && vctl start --tag {agent_id}"
        
        return_code, stdout, stderr = await ansible.run_volttron_ad_hoc(
            command=cmd,
            hosts=platform.config.instance_name,
            connection=host.ansible_connection
        )

        if return_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start agent {agent_id}: {stderr or stdout}"
            )
        return {"status": "success", "message": f"Agent {agent_id} started successfully", "output": stdout}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@ansible_router.get("/platform/{platform_id}/logs")
async def get_platform_logs(platform_id: str, lines: int = 100):
    """Fetch VOLTTRON log contents from remote platform"""
    try:
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)
        
        if not platform:
            raise HTTPException(status_code=404, detail="Platform not found")
        
        ansible = await get_ansible_service()
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()
        
        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )
        
        host = all_hosts[platform.config.instance_name]
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"
        
        # Tail the log file - use simple command to avoid quote escaping issues with Ansible
        cmd = f"tail -n {lines} {volttron_home}/volttron.log || echo NO_LOG_FILE"
        
        return_code, stdout, stderr = await ansible.run_volttron_ad_hoc(
            command=cmd,
            hosts=platform.config.instance_name,
            connection=host.ansible_connection
        )
        
        # Parse Ansible output to extract actual command stdout
        # The Ansible ad_hoc playbook wraps the output in "standard out:\n..."
        log_content = "No logs available"
        
        # Try to extract the actual stdout from Ansible's output
        import re
        # Look for "standard out:\n" followed by the actual content
        match = re.search(r'"standard out:\\n([^"]*)"', stdout, re.DOTALL)
        if match:
            # Unescape the newlines
            log_content = match.group(1).replace('\\n', '\n')
        elif "NO_LOG_FILE" in stdout:
            log_content = f"No log file detected at: {volttron_home}/volttron.log\n\nVOLTTRON may not have been started yet, or logging is not configured."
        
        return {
            "logs": log_content,
            "log_path": f"{volttron_home}/volttron.log",
            "error": stderr if stderr else None
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch logs: {str(e)}"
        )

@ansible_router.delete("/platform/{platform_id}/logs")
async def delete_platform_logs(platform_id: str):
    """Delete VOLTTRON log file from remote platform"""
    try:
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)
        
        if not platform:
            raise HTTPException(status_code=404, detail="Platform not found")
        
        ansible = await get_ansible_service()
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()
        
        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )
        
        host = all_hosts[platform.config.instance_name]
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"
        
        # Delete the log file
        cmd = f"rm -f {volttron_home}/volttron.log && echo LOG_DELETED"
        
        return_code, stdout, stderr = await ansible.run_volttron_ad_hoc(
            command=cmd,
            hosts=platform.config.instance_name,
            connection=host.ansible_connection
        )
        
        if "LOG_DELETED" in stdout or return_code == 0:
            return {"message": "Log file deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete log file")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete logs: {str(e)}"
        )

@ansible_router.post("/stop_agent/{platform_id}/{agent_id}")
async def stop_agent(platform_id: str, agent_id: str, ansible: AnsibleService = Depends(get_ansible_service)):
    """Stops a specific agent on a VOLTTRON platform using vctl"""
    try:
        # Get platform definition and host entry
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)
        
        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")
        
        # Get host entry from inventory
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()
        
        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )
        
        host = all_hosts[platform.config.instance_name]
        
        # Build command to stop the agent
        venv_path = host.volttron_venv if host.volttron_venv else "~/.local"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"
        
        cmd = f"export VOLTTRON_HOME={volttron_home} && source {venv_path}/bin/activate && vctl stop --tag {agent_id}"
        
        return_code, stdout, stderr = await ansible.run_volttron_ad_hoc(
            command=cmd,
            hosts=platform.config.instance_name,
            connection=host.ansible_connection
        )

        if return_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to stop agent {agent_id}: {stderr or stdout}"
            )
        return {"status": "success", "message": f"Agent {agent_id} stopped successfully", "output": stdout}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


INSTALL_AGENT_TIMEOUT = int(os.getenv("INSTALL_AGENT_TIMEOUT", "120"))


@ansible_router.post("/install_agent/{platform_id}")
async def install_agent(
    platform_id: str,
    agent_identity: str,
    agent_source: str,
    start_agent: bool = True,
    agent_config: str = None,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Install an agent on a running VOLTTRON platform using vctl install.

    Args:
        platform_id: The platform instance name
        agent_identity: The VIP identity for the agent
        agent_source: The pip package name or path to install (e.g., 'volttron-listener')
        start_agent: Whether to start the agent after installation (default: True)
        agent_config: Optional path to agent config file on remote system
    """
    try:
        # Get platform definition and host entry
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)

        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

        # Get host entry from inventory
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()

        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )

        host = all_hosts[platform.config.instance_name]

        # Build paths
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"

        # For modular VOLTTRON, agents are installed as pip packages
        # Then we need to create an agent configuration and start it
        agent_source_arg = shlex.quote(agent_source)
        agent_identity_arg = shlex.quote(agent_identity)

        install_cmd_parts = [
            f"export VOLTTRON_HOME={volttron_home}",
            f"source {venv_path}/bin/activate",
            # Install the agent package via pip
            f"pip install {agent_source_arg}",
        ]

        # For modular VOLTTRON, we need to use vctl to register and start the agent
        # The agent package is already installed, now we just need to configure it
        if start_agent:
            # TODO: For modular VOLTTRON, starting agents works differently
            # Need to determine the correct approach based on the volttron-ansible version
            pass

        cmd = " && ".join(install_cmd_parts)

        logger.info(f"Installing agent {agent_identity} on platform {platform_id}: {agent_source}")

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=120)

        if return_code != 0:
            error_msg = stderr or stdout
            logger.error(f"Failed to install agent {agent_identity}: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to install agent {agent_identity}: {error_msg}"
            )

        logger.info(f"Agent {agent_identity} installed successfully on platform {platform_id}")
        return {
            "status": "success",
            "message": f"Agent {agent_identity} installed successfully",
            "output": stdout,
            "agent_identity": agent_identity,
            "started": start_agent
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing agent: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@ansible_router.post("/remove_agent/{platform_id}/{agent_identity}")
async def remove_agent(
    platform_id: str,
    agent_identity: str,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Remove/uninstall an agent from a running VOLTTRON platform using vctl remove.

    Args:
        platform_id: The platform instance name
        agent_identity: The VIP identity of the agent to remove
    """
    try:
        # Get platform definition and host entry
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)

        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

        # Get host entry from inventory
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()

        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )

        host = all_hosts[platform.config.instance_name]

        # Build paths
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"

        # First, get the agent UUID from the identity using vctl status --json
        status_cmd = f"export VOLTTRON_HOME={volttron_home} && source {venv_path}/bin/activate && vctl --json status"

        return_code, stdout, stderr = await ansible.run_ssh_command(host, status_cmd, timeout=30)

        if return_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get agent status: {stderr or stdout}"
            )

        # Parse the JSON output to find the agent UUID
        import json
        try:
            agents = json.loads(stdout)
            agent_uuid = None
            for identity, agent_info in agents.items():
                if identity == agent_identity:
                    agent_uuid = agent_info.get("agent_uuid")
                    break

            if not agent_uuid:
                raise HTTPException(
                    status_code=404,
                    detail=f"Agent {agent_identity} not found on platform"
                )
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse agent status: {stdout}"
            )

        # Now remove the agent using its UUID
        remove_cmd = f"export VOLTTRON_HOME={volttron_home} && source {venv_path}/bin/activate && vctl remove {agent_uuid}"

        logger.info(f"Removing agent {agent_identity} (UUID: {agent_uuid}) from platform {platform_id}")

        return_code, stdout, stderr = await ansible.run_ssh_command(host, remove_cmd, timeout=30)

        if return_code != 0:
            error_msg = stderr or stdout
            logger.error(f"Failed to remove agent {agent_identity}: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove agent {agent_identity}: {error_msg}"
            )

        logger.info(f"Agent {agent_identity} removed successfully from platform {platform_id}")
        return {
            "status": "success",
            "message": f"Agent {agent_identity} removed successfully",
            "output": stdout,
            "agent_identity": agent_identity
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing agent: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@ansible_router.get("/ping/{id}")
async def ping_host(id: str, ansible: AnsibleService = Depends(get_ansible_service)):
    """Pings a specific host using Ansible"""
    try:
        inventory_service = await get_inventory_service()
        entry = await inventory_service.get_host(id)
        if not entry:
            raise HTTPException(status_code=404, detail="Host entry not found")
        
        return_code, stdout, stderr = await ansible.run_module("ping", entry.ansible_host)

        if return_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to ping host: {stderr or stdout}"
            )

        return {"status": "success", "output": stdout}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@ansible_router.post("/detect_existing_volttron")
async def detect_existing_volttron(
    ssh_host: str,
    ssh_user: str,
    ssh_port: str = "22",
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Detect an existing VOLTTRON installation on a remote machine.

    This probes the remote machine via SSH to find VOLTTRON installations
    and returns detected paths and status.
    """
    try:
        # Create a temporary host entry for SSH connection
        from .models import HostEntry
        temp_host = HostEntry(
            id=ssh_host,
            ansible_user=ssh_user,
            ansible_host=ssh_host,
            ansible_port=int(ssh_port),
            ansible_connection="ssh"
        )

        result = {
            "volttron_found": False,
            "volttron_home": "~/.volttron",
            "volttron_venv": "~/volttron.venv",
            "is_running": False,
            "ssh_ok": False
        }

        # First, test SSH connection
        test_cmd = "echo SSH_OK"
        return_code, stdout, stderr = await ansible.run_ssh_command(temp_host, test_cmd, timeout=10)
        if "SSH_OK" not in stdout:
            raise HTTPException(status_code=400, detail="Could not establish SSH connection")

        result["ssh_ok"] = True

        # Check common VOLTTRON paths
        # Check for venv in common locations
        venv_check_cmd = """
            if [ -f ~/volttron.venv/bin/activate ]; then echo "VENV:~/volttron.venv";
            elif [ -f ~/.volttron.venv/bin/activate ]; then echo "VENV:~/.volttron.venv";
            elif [ -f ~/venv/bin/activate ]; then echo "VENV:~/venv";
            elif [ -f /opt/volttron/venv/bin/activate ]; then echo "VENV:/opt/volttron/venv";
            else echo "VENV:NOT_FOUND"; fi
        """
        return_code, stdout, stderr = await ansible.run_ssh_command(temp_host, venv_check_cmd, timeout=10)
        if "VENV:" in stdout and "NOT_FOUND" not in stdout:
            venv_path = stdout.split("VENV:")[1].strip().split()[0]
            result["volttron_venv"] = venv_path
            result["volttron_found"] = True

        # Check for VOLTTRON_HOME in common locations
        home_check_cmd = """
            if [ -d ~/.volttron ]; then echo "HOME:~/.volttron";
            elif [ -d /var/lib/volttron ]; then echo "HOME:/var/lib/volttron";
            elif [ -d /opt/volttron/home ]; then echo "HOME:/opt/volttron/home";
            else echo "HOME:NOT_FOUND"; fi
        """
        return_code, stdout, stderr = await ansible.run_ssh_command(temp_host, home_check_cmd, timeout=10)
        if "HOME:" in stdout and "NOT_FOUND" not in stdout:
            home_path = stdout.split("HOME:")[1].strip().split()[0]
            result["volttron_home"] = home_path
            result["volttron_found"] = True

        # Check if VOLTTRON is running using vctl status
        venv_path = result["volttron_venv"]
        volttron_home = result["volttron_home"]
        status_cmd = f"export VOLTTRON_HOME={volttron_home} && source {venv_path}/bin/activate && vctl status > /dev/null 2>&1 && echo RUNNING || echo STOPPED"
        return_code, stdout, stderr = await ansible.run_ssh_command(temp_host, status_cmd, timeout=15)
        result["is_running"] = "RUNNING" in stdout and "STOPPED" not in stdout

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Detection failed: {str(e)}"
        )


@catalog_router.get("/agents", response_model=dict[str, AgentType])
async def get_agent_catalog() -> dict[str, AgentType]:
    """Retrieves the agent catalog"""
    try:
        catalog = AgentCatalog()
        return catalog.agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@catalog_router.get("/agents/{identity}", response_model=AgentType)
async def get_agent_from_catalog(identity: str) -> AgentType:
    """Retrieves a specific agent from the catalog by its identity"""
    try:
        catalog = AgentCatalog()
        agent = catalog.get_agent(identity)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found in catalog")
        return agent
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@tool_management_router.post("/start_tool")
async def start_tool(request: ToolRequest):
    """Start a specific tool service on demand."""
    result = ToolManager.start_tool_service(
        tool_name=request.tool_name,
        module_path=request.module_path,
        use_poetry=request.use_poetry
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result

@tool_management_router.post("/stop_tool/{tool_name}", response_model=dict[str, str | bool])
async def stop_tool(tool_name: str):
    from loguru import logger
    """Stop a specific tool service."""
    result = ToolManager.stop_tool_service(tool_name=tool_name)
    logger.debug(result)
    if not result["success"] and "not running" not in result["message"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    if "not running" in result["message"]:
        return {"success": True, "message": f"Tool '{tool_name}' is already stopped"}

    return result

@tool_management_router.get("/tool_status/{tool_name}", response_model=ToolStatusResponse)
async def tool_status(tool_name: str):
    """Check if a specific tool is running."""
    is_running = ToolManager.is_tool_running(tool_name)
    if is_running:
        port = ToolManager.get_tool_port(tool_name) if is_running else None
        return ToolStatusResponse(
            tool_name= tool_name,
            tool_running=is_running,
            port=port
        )
    return ToolStatusResponse(
        tool_name= tool_name,
        tool_running=is_running,
        port=None
    )



@bacnet_scan_api_router.get("/get_local_ip", response_model=dict[str, str])
async def bacnet_scan_get_local_ip(target_ip: str = None) -> dict[str, str]:
    # OPTIONAL
    from .tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/get_local_ip")
    REQUEST = {"target_ip" : target_ip}
    try:
        response = await ToolProxyFactory.request(
            url,
            "GET",
            data=REQUEST
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/start_proxy", response_model=dict[str, Any])
async def bacnet_scan_start_proxy(local_device_address: str | None = None) -> dict[str, Any]:
    from .tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/start_proxy")
    REQUEST = {"local_device_address" : local_device_address}
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.get("/get_host_ip", response_model=dict)
async def bacnet_scan_get_host_ip() -> dict:
    # OPTIONAL, for WSL2 users
    from .tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/get_host_ip")
    try:
        response = await ToolProxyFactory.request(
            url,
            "GET",
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.get("/discover_networks", response_model=dict)
async def bacnet_discover_networks(verbose: bool = False) -> dict:
    """Discover available networks for BACnet scanning using comprehensive network analysis."""
    from .tool_proxy_factory import ApiError

    url = get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/discover_networks")
    try:
        response = await ToolProxyFactory.request(
            url,
            "GET",
            params={"verbose": verbose}
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
@bacnet_scan_api_router.post("/bacnet/scan_subnet", response_model=ScanResponse)
async def bacnet_scan_subnet(network_str: str | None = None) -> dict[str, str]:
    from .tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/bacnet/scan_subnet")
    REQUEST={"subnet": network_str}
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST,
            timeout=600.0
        )
        data = response.json()
        return ScanResponse(
            **data
        )
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
@bacnet_scan_api_router.post("/read_property", response_model=dict)
async def bacnet_scan_read_property(request: BACnetReadPropertyRequest) -> dict:
    from .tool_proxy_factory import ApiError
    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/read_property")
    REQUEST = {
            "device_address": request.device_address,
            "object_identifier": request.object_identifier,
            "property_identifier": request.property_identifier,
            # "property_array_index": request.property_array_index
        }
    if request.property_array_index is not None:
        REQUEST["property_array_index"] = request.property_array_index
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/write_property", response_model=dict)
async def bacnet_scan_write_property(request: BACnetWritePropertyRequest) -> dict:
    from .tool_proxy_factory import ApiError
    from loguru import logger
    
    logger.debug(f"this is i, the endpiont getting: {request}")
    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/write_property")
    REQUEST = {
            "device_address": request.device_address,
            "object_identifier": request.object_identifier,
            "property_identifier": request.property_identifier,
            "value": request.value,
            "priority": request.priority,
            # "property_array_index": request.property_array_index
        }
    if request.property_array_index is not None:
        REQUEST["property_array_index"] = request.property_array_index
    logger.debug(f"this is i, the endpoint, passing in: {REQUEST}")
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            params=REQUEST
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/bacnet/read_device_all")
async def bacnet_scan_read_device_all(request: BACnetReadDeviceAllRequest):
    from .tool_proxy_factory import ApiError
    from loguru import logger
    logger.debug(f"this is i, the endpiont getting: {request}")

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/bacnet/read_device_all")
    REQUEST={
        "device_address": request.device_address,
        "device_object_identifier": request.device_object_identifier
        }
    logger.debug(f"and this is my REQUEST: {REQUEST}")

    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST,
            timeout=600.0
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/bacnet/who_is")
async def bacnet_scan_who_is(
        device_instance_low: int,
        device_instance_high: int,
        dest: str
    ) -> dict[str, str]:
    from .tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/bacnet/who_is")
    REQUEST={
        "device_instance_low": device_instance_low,
        "device_instance_high": device_instance_high,
        "dest": dest
        }
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/stop_proxy", response_model=dict[str, Any])
async def bacnet_scan_stop_proxy() -> dict[str, Any]:
    from .tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/stop_proxy")
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
@bacnet_scan_api_router.post("/bacnet/read_object_list_names", response_model=ObjectListNamesResponse)
async def bacnet_scan_read_object_list_names(
    device_address: str, 
    device_object_identifier: str,
    page: int = 1,
    page_size: int = 100
) -> ObjectListNamesResponse:
    from .tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/bacnet/read_object_list_names")
    REQUEST = {
        "device_address": device_address,
        "device_object_identifier": device_object_identifier,
        "page": page,
        "page_size": page_size
    }
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST
        )
        data = response.json()
        return ObjectListNamesResponse(**data)
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
