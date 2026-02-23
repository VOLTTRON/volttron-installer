from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Any, Optional
from ..utils import get_api_url
import os, asyncio, shlex, re
from loguru import logger

from volttron_installer.backend.tool_manager import ToolManager
from volttron_installer.backend.services.ansible_service import AnsibleService, get_ansible_service
from volttron_installer.backend.services.inventory_service import InventoryService, get_inventory_service
from volttron_installer.backend.services.platform_service import PlatformService, get_platform_service
from volttron_installer.backend.services.github_agent_service import fetch_github_agents
from volttron_installer.backend.services.local_agent_service import scan_local_agents
from volttron_installer.backend.models import AgentCatalog
from volttron_installer.settings import get_settings

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
    GitHubAgentsResponse,
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

# Deployment progress tracking (in-memory)
DEPLOY_PROGRESS: dict[str, dict] = {}


def _init_deploy_progress(platform_id: str, total_steps: int | None = None) -> None:
    DEPLOY_PROGRESS[platform_id] = {
        "status": "running",
        "current_task": "Starting deployment...",
        "progress": 0,
        "steps": [],
        "logs": [],
        "total_steps": total_steps,
    }


def _append_deploy_log(platform_id: str, message: str) -> None:
    if platform_id not in DEPLOY_PROGRESS:
        _init_deploy_progress(platform_id)
    DEPLOY_PROGRESS[platform_id]["logs"].append(message)


def _set_deploy_step(platform_id: str, step_name: str, status: str, progress: int | None = None) -> None:
    if platform_id not in DEPLOY_PROGRESS:
        _init_deploy_progress(platform_id)
    steps = DEPLOY_PROGRESS[platform_id]["steps"]
    for step in steps:
        if step["name"] == step_name:
            step["status"] = status
            break
    else:
        steps.append({"name": step_name, "status": status})

    DEPLOY_PROGRESS[platform_id]["current_task"] = step_name
    if progress is not None:
        DEPLOY_PROGRESS[platform_id]["progress"] = progress


def _finalize_deploy_progress(platform_id: str, status: str) -> None:
    if platform_id not in DEPLOY_PROGRESS:
        _init_deploy_progress(platform_id)
    DEPLOY_PROGRESS[platform_id]["status"] = status
    if status == "success":
        DEPLOY_PROGRESS[platform_id]["progress"] = 100

@ansible_router.get("/hosts", response_model=list[HostEntry])
async def get_hosts() -> list[HostEntry]:
    """Retrieves a list of `HostEntry` items"""
    try:
        inventory_service = await get_inventory_service()
        hosts = await inventory_service.get_hosts()
        return list(hosts.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@ansible_router.get("/hosts/{id}", response_model=HostEntry)
async def get_host_id(id: str) -> HostEntry:
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
        raise HTTPException(status_code=500, detail=str(e))

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
            ansible_connection=host_entry.ansible_connection,
            http_proxy=host_entry.http_proxy,
            https_proxy=host_entry.https_proxy,
            volttron_venv=host_entry.volttron_venv,
            volttron_home=host_entry.volttron_home,
            volttron_source=host_entry.volttron_source,
            host_configs_dir=host_entry.host_configs_dir,
            instance_name=host_entry.instance_name,
            ignore_host_keys=host_entry.ignore_host_keys
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
    try:
        status = await ansible_service.get_platform_status(platform_id)

        if status is None:
            raise HTTPException(status_code=404, detail="Platform not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@platform_router.get("/connection/{platform_id}")
async def check_platform_connection(
        platform_id: str,
        ansible_service: AnsibleService = Depends(get_ansible_service)):
    """Quick connection check for a platform"""
    try:
        is_connected, connection_method, error = await ansible_service.check_host_connection(platform_id)

        return {
            "connected": is_connected,
            "connection_method": connection_method,
            "error": error
        }
    except Exception as e:
        return {
            "connected": False,
            "connection_method": "unknown",
            "error": str(e)
        }

@platform_router.post("/mark-deployed/{platform_id}")
async def mark_platform_deployed(
        platform_id: str,
        deployed: bool = True,
        platform_service: PlatformService = Depends(get_platform_service)):
    """Mark a platform as deployed (or not deployed) without running deployment.

    Useful for existing platforms that were deployed before the deployed flag was persisted.
    """
    try:
        platform = await platform_service.get_platform(platform_id)
        if platform is None:
            raise HTTPException(status_code=404, detail="Platform not found")

        platform.deployed = deployed
        await platform_service.update_platform(platform_id, platform)

        return {"status": "success", "deployed": deployed}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            "ping", "-c", "1", "-W", "3", host_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await asyncio.wait_for(process.communicate(), timeout=5)

        # If returncode is 0, the host is reachable
        return {"reachable": process.returncode == 0}

    except (asyncio.TimeoutError, Exception):
        # Timeout or any error means the host is not reachable
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


async def _select_python_cmd_for_host(host: HostEntry, ansible: AnsibleService, custom_python_path: str = "") -> str:
    """Select a supported Python command on the remote host (requires 3.10).
    
    Args:
        host: Remote host entry
        ansible: Ansible service for running SSH commands
        custom_python_path: Optional custom Python path (e.g., ~/.pyenv/versions/3.10.14/bin/python3)
    
    Returns:
        Python command to use for deployment
    """
    # If custom Python path is provided, verify it and use it
    if custom_python_path:
        # Expand tilde to home directory
        test_cmd = custom_python_path.replace("~", "$HOME")
        ret, stdout, stderr = await ansible.run_ssh_command(host, f"{test_cmd} -V 2>&1", timeout=10)
        if ret != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Custom Python path '{custom_python_path}' not found or not executable: {stderr or stdout}"
            )
        
        version_output = (stdout or stderr).strip()
        match = re.search(r"Python\s+(\d+)\.(\d+)", version_output)
        if not match:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to detect Python version from custom path. Output: {version_output}"
            )
        
        major, minor = int(match.group(1)), int(match.group(2))
        if major != 3 or minor != 10:
            raise HTTPException(
                status_code=500,
                detail=f"Custom Python path must be Python 3.10, but found: {version_output}"
            )
        
        return test_cmd
    
    # Auto-detect Python 3.10
    ret, stdout, stderr = await ansible.run_ssh_command(host, "python3 -V 2>&1", timeout=10)
    version_output = (stdout or stderr).strip()

    match = re.search(r"Python\s+(\d+)\.(\d+)", version_output)
    if not match:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to detect Python version on remote host. Output: {version_output}"
        )

    major, minor = int(match.group(1)), int(match.group(2))
    if major == 3 and minor == 10:
        return "python3"

    ret, stdout, _ = await ansible.run_ssh_command(host, "command -v python3.10", timeout=10)
    if ret == 0 and stdout.strip():
        return "python3.10"

    # Try pyenv-managed Python 3.10 without changing global
    pyenv_python = "$HOME/.pyenv/versions/3.10.14/bin/python3"
    ret, stdout, _ = await ansible.run_ssh_command(host, f"test -x {pyenv_python} && echo OK", timeout=10)
    if ret == 0 and "OK" in stdout:
        return pyenv_python

    suggestion = (
        "Python 3.10 is required.\n\n"
        "Install via pyenv (without changing system Python):\n"
        "curl https://pyenv.run | bash && \\\n"
        "echo 'export PATH=\"$HOME/.pyenv/bin:$PATH\"' >> ~/.bashrc && \\\n"
        "echo 'eval \"$(pyenv init -)\"' >> ~/.bashrc && \\\n"
        "echo 'eval \"$(pyenv virtualenv-init -)\"' >> ~/.bashrc && \\\n"
        "source ~/.bashrc && \\\n"
        "pyenv install 3.10.14\n\n"
        "After installation, add the path to Advanced Settings:\n"
        "~/.pyenv/versions/3.10.14/bin/python3"
    )
    raise HTTPException(
        status_code=500,
        detail=f"Unsupported Python version: {version_output}. {suggestion}"
    )


@platform_router.get("/deploy_progress/{platform_id}")
async def get_deploy_progress(platform_id: str):
    """Return current deployment progress for a platform."""
    return DEPLOY_PROGRESS.get(
        platform_id,
        {
            "status": "idle",
            "current_task": "",
            "progress": 0,
            "steps": [],
            "logs": [],
            "total_steps": None,
        },
    )


@platform_router.post("/install_python310/{platform_id}")
async def install_python310(platform_id: str,
                            ansible: AnsibleService = Depends(get_ansible_service),
                            platform_service: PlatformService = Depends(get_platform_service),
                            inventory_service: InventoryService = Depends(get_inventory_service)):
    """Install Python 3.10 via pyenv and create the VOLTTRON venv using it."""
    platform = await platform_service.get_platform(platform_id)
    if platform is None:
        raise HTTPException(status_code=404, detail="Platform not found")

    all_hosts = await inventory_service.get_hosts()
    if platform.config.instance_name not in all_hosts:
        raise HTTPException(status_code=404, detail=f"Host {platform.config.instance_name} not found in inventory")

    host = all_hosts[platform.config.instance_name]
    venv_path = host.volttron_venv or "~/volttron.venv"

    script = f'''
VENV_PATH="{venv_path}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
PYENV_ROOT="$HOME/.pyenv"
PYENV_BIN="$PYENV_ROOT/bin/pyenv"
PYENV_PY="$PYENV_ROOT/versions/3.10.14/bin/python3"

# Always ensure dependencies are installed
sudo apt-get update && sudo apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libffi-dev liblzma-dev libncurses5-dev libncursesw5-dev tk-dev curl git

if [ ! -x "$PYENV_BIN" ]; then
  curl https://pyenv.run | bash
fi

export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

$PYENV_BIN install -s 3.10.14

if [ ! -x "$PYENV_PY" ]; then
  echo "VOLTTRON_FAILED: pyenv python not found at $PYENV_PY"
  exit 1
fi

$PYENV_PY -m venv "$VENV_PATH"
echo "PYENV_READY"
'''

    return_code, stdout, stderr = await ansible.run_ssh_command(host, script, timeout=900)
    if return_code != 0 or "PYENV_READY" not in stdout:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to install Python 3.10 with pyenv: {stderr or stdout}"
        )

    # Update platform config with the custom Python path
    platform.config.custom_python_path = "~/.pyenv/versions/3.10.14/bin/python3"
    await platform_service.update_platform(platform.config.instance_name, platform)

    return {"status": "success", "message": "Python 3.10 installed via pyenv and venv created.", "custom_python_path": "~/.pyenv/versions/3.10.14/bin/python3"}

async def _deploy_modular_via_ssh(
    host: HostEntry,
    config: PlatformConfig,
    ansible: AnsibleService,
    python_cmd: str = "python3",
    platform_id: str | None = None
) -> dict:
    """
    Deploy modular VOLTTRON using direct SSH commands instead of Ansible playbooks.
    This is simpler, faster, and gives us more control over versions.

    Supports:
    - PyPI versions: "2.0.0rc20"
    - Git URLs: "git+https://github.com/username/volttron-core@branch"
    - Empty string: latest from PyPI

    TODO: Consider moving this to Ansible playbook later if needed for more complex deployments.
    """
    venv_path = host.volttron_venv or "~/volttron.venv"
    volttron_home = host.volttron_home or "~/.volttron"

    # Determine volttron-core package specification
    # Supports: empty (latest), version number, or git URL
    if config.volttron_version:
        if config.volttron_version.startswith("git+"):
            # Git URL provided directly (e.g., git+https://github.com/user/volttron-core@develop)
            core_pkg = config.volttron_version
        elif "/" in config.volttron_version or "@" in config.volttron_version:
            # Shorthand git URL (e.g., eclipse-volttron/volttron-core@develop)
            core_pkg = f"git+https://github.com/{config.volttron_version}"
        else:
            # Version number provided (e.g., 2.0.0rc20)
            core_pkg = f"volttron-core=={config.volttron_version}"
    else:
        # Default to latest from PyPI
        core_pkg = "volttron-core"

    steps = []

    total_steps = 7
    if platform_id:
        _init_deploy_progress(platform_id, total_steps=total_steps)

    # Step 1: Kill any existing VOLTTRON processes
    cmd = f"pkill -9 -f 'volttron -vv' 2>/dev/null || true"
    logger.info(f"[DEPLOY] Step 1: Killing existing VOLTTRON processes")
    if platform_id:
        _set_deploy_step(platform_id, "Kill existing processes", "running", progress=5)
        _append_deploy_log(platform_id, "[Step 1] Killing existing VOLTTRON processes")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)
    steps.append({"step": "Kill existing processes", "success": True, "output": stdout, "error": stderr})
    if platform_id:
        _set_deploy_step(platform_id, "Kill existing processes", "success", progress=10)
    # Don't fail if no processes to kill

    # Step 2: Create virtual environment
    cmd = f"{python_cmd} -m venv {venv_path}"
    logger.info(f"[DEPLOY] Step 2: Creating venv - {cmd}")
    if platform_id:
        _set_deploy_step(platform_id, "Create venv", "running", progress=20)
        _append_deploy_log(platform_id, f"[Step 2] Creating venv with {python_cmd}")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=60)
    steps.append({"step": "Create venv", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Create venv", "failed", progress=20)
        raise HTTPException(status_code=500, detail=f"Failed to create venv: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Create venv", "success", progress=25)

    # Step 3: Upgrade pip
    cmd = f"source {venv_path}/bin/activate && pip install --upgrade pip"
    logger.info(f"[DEPLOY] Step 3: Upgrading pip - {cmd}")
    if platform_id:
        _set_deploy_step(platform_id, "Upgrade pip", "running", progress=35)
        _append_deploy_log(platform_id, "[Step 3] Upgrading pip")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=120)
    steps.append({"step": "Upgrade pip", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Upgrade pip", "failed", progress=35)
        raise HTTPException(status_code=500, detail=f"Failed to upgrade pip: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Upgrade pip", "success", progress=40)

    # Step 4: Install VOLTTRON libraries first (these pull in dependencies like pyzmq)
    # This may install volttron-core from PyPI as a dependency
    cmd = f"source {venv_path}/bin/activate && pip install volttron-lib-zmq volttron-lib-auth"
    logger.info(f"[DEPLOY] Step 4: Installing VOLTTRON libraries")
    if platform_id:
        _set_deploy_step(platform_id, "Install VOLTTRON libs", "running", progress=55)
        _append_deploy_log(platform_id, "[Step 4] Installing VOLTTRON libs")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=300)
    steps.append({"step": "Install VOLTTRON libs", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Install VOLTTRON libs", "failed", progress=55)
        raise HTTPException(status_code=500, detail=f"Failed to install VOLTTRON libs: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Install VOLTTRON libs", "success", progress=60)

    # Step 5: Force reinstall volttron-core from the specified source
    # This overwrites any PyPI version that was pulled in by the libs
    cmd = f"source {venv_path}/bin/activate && pip install --no-cache-dir --force-reinstall {core_pkg}"
    logger.info(f"[DEPLOY] Step 5: Installing volttron-core - {core_pkg}")
    if platform_id:
        _set_deploy_step(platform_id, f"Install volttron-core ({core_pkg})", "running", progress=75)
        _append_deploy_log(platform_id, f"[Step 5] Installing volttron-core ({core_pkg})")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=300)
    steps.append({"step": f"Install volttron-core ({core_pkg})", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, f"Install volttron-core ({core_pkg})", "failed", progress=75)
        raise HTTPException(status_code=500, detail=f"Failed to install volttron-core: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, f"Install volttron-core ({core_pkg})", "success", progress=80)

    # Step 6: Create VOLTTRON_HOME directory
    cmd = f"mkdir -p {volttron_home}"
    logger.info(f"[DEPLOY] Step 6: Creating VOLTTRON_HOME - {cmd}")
    if platform_id:
        _set_deploy_step(platform_id, "Create VOLTTRON_HOME", "running", progress=90)
        _append_deploy_log(platform_id, "[Step 6] Creating VOLTTRON_HOME")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)
    steps.append({"step": "Create VOLTTRON_HOME", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Create VOLTTRON_HOME", "failed", progress=90)
        raise HTTPException(status_code=500, detail=f"Failed to create VOLTTRON_HOME: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Create VOLTTRON_HOME", "success", progress=92)

    # Step 7: Write config file
    # Note: modular VOLTTRON uses 'messagebus' not 'message-bus', and doesn't use 'vip-address' in config
    config_content = f"""[volttron]
instance-name = {config.instance_name}
messagebus = {config.message_bus}
"""
    # Escape for shell
    config_escaped = config_content.replace("'", "'\\''")
    cmd = f"echo '{config_escaped}' > {volttron_home}/config"
    logger.info(f"[DEPLOY] Step 7: Writing config file")
    if platform_id:
        _set_deploy_step(platform_id, "Write config", "running", progress=96)
        _append_deploy_log(platform_id, "[Step 7] Writing config file")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)
    steps.append({"step": "Write config", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Write config", "failed", progress=96)
        raise HTTPException(status_code=500, detail=f"Failed to write config: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Write config", "success", progress=100)

    logger.info(f"[DEPLOY] Modular VOLTTRON deployed successfully")
    if platform_id:
        _finalize_deploy_progress(platform_id, "success")
    return {
        "status": "success",
        "message": "Modular VOLTTRON deployed via SSH",
        "steps": steps
    }


@platform_router.post("/deploy/{platform_id}")
async def deploy_platform(platform_id: str, password:str,
                          ansible: AnsibleService = Depends(get_ansible_service),
                          platform_service: PlatformService = Depends(get_platform_service),
                          inventory_service: InventoryService = Depends(get_inventory_service)):

    """Deploys a platform using SSH commands for modular, Ansible for monolithic"""
    try:
        platform = await platform_service.get_platform(platform_id)
        if platform is None:
            raise HTTPException(status_code=404, detail="Platform not found")

        # Get host entry from inventory
        all_hosts = await inventory_service.get_hosts()
        if platform.config.instance_name not in all_hosts:
            raise HTTPException(status_code=404, detail=f"Host {platform.config.instance_name} not found in inventory")

        host = all_hosts[platform.config.instance_name]
        ignore_host_keys = host.ignore_host_keys
        target_host = platform.config.instance_name

        # Branch based on VOLTTRON type
        if platform.config.volttron_type == "modular":
            # Use simple SSH-based deployment for modular VOLTTRON
            logger.info(f"[DEPLOY] Deploying modular VOLTTRON for {platform_id}")

            _init_deploy_progress(platform_id, total_steps=7)
            DEPLOY_PROGRESS[platform_id]["current_task"] = "Preflight: Checking Python version"

            python_cmd = await _select_python_cmd_for_host(host, ansible, platform.config.custom_python_path)
            _append_deploy_log(platform_id, f"Preflight OK: using {python_cmd}")

            result = await _deploy_modular_via_ssh(
                host,
                platform.config,
                ansible,
                python_cmd=python_cmd,
                platform_id=platform_id
            )

            # Mark platform as deployed
            platform.deployed = True
            await platform_service.update_platform(platform.config.instance_name, platform)

            return {
                "status": "success",
                "output": f"Modular VOLTTRON deployed successfully\n\nSteps:\n" +
                         "\n".join([f"- {s['step']}: {'OK' if s['success'] else 'FAILED'}" for s in result.get('steps', [])]),
                "stderr": "",
                "tasks": [{"name": s["step"], "status": "ok" if s["success"] else "failed"} for s in result.get("steps", [])]
            }

        else:
            # Use Ansible playbooks for monolithic VOLTTRON
            # TODO: Could also convert this to SSH-based later
            logger.info(f"[DEPLOY] Deploying monolithic VOLTTRON for {platform_id} via Ansible")
            _init_deploy_progress(platform_id)
            DEPLOY_PROGRESS[platform_id]["current_task"] = "Running Ansible playbooks"

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

            # Clean up config file - remove duplicate snake_case fields and installer-only fields
            volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"
            cleanup_cmd = f"sed -i '/^instance_name =/d; /^messagebus =/d; /^message_bus =/d; /^options =/d; /^vip_address =/d; /^volttron_type =/d' {volttron_home}/config"
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
            # TODO: For modular, agents are installed via vctl install in the install_agent endpoint
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

    except HTTPException as e:
        _finalize_deploy_progress(platform_id, "failed")
        _append_deploy_log(platform_id, f"ERROR: {e.detail}")
        raise
    except Exception as e:
        _finalize_deploy_progress(platform_id, "failed")
        _append_deploy_log(platform_id, f"ERROR: {str(e)}")
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
        # Also disable agent-isolation-mode which causes poetry issues in VOLTTRON_HOME
        # Use direct SSH for speed and reliability
        cleanup_cmd = f"sed -i '/instance_name/d; /messagebus/d; /message_bus/d; /^options/d; /vip_address/d; /volttron_type/d; s/agent-isolation-mode = True/agent-isolation-mode = False/g' {volttron_home}/config 2>/dev/null || true"
        await ansible.run_ssh_command(host, cleanup_cmd, timeout=10)

        # SSH startup: activate venv, set VOLTTRON_HOME, start in background
        # Use proper volttron command (not nohup workaround) to ensure setup_poetry_project() is called
        # Logs go to VOLTTRON_HOME/volttron.log
        startup_cmd = f'''
VENV_PATH="{venv_path}"
VOLTTRON_HOME="{volttron_home}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
export VOLTTRON_HOME

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
    exit 1
fi
. "$VENV_PATH/bin/activate"
mkdir -p "$VOLTTRON_HOME"

nohup volttron -vv -l "$VOLTTRON_HOME/volttron.log" </dev/null &>/dev/null &
disown
echo "VOLTTRON_STARTED"
'''

        logger.info(f"[START] Starting VOLTTRON via direct SSH for platform {platform_id}")
        return_code, stdout, stderr = await ansible.run_ssh_command(host, startup_cmd, timeout=30)

        logger.debug(f"Startup result - return_code: {return_code}, stdout: {stdout[:500]}, stderr: {stderr[:500]}")

        if "VOLTTRON_STARTED" in stdout:
            return {"status": "success", "message": "Platform start command issued."}
        elif "VOLTTRON_FAILED" in stdout:
            log_output = stdout.split("VOLTTRON_FAILED:")[-1].strip() if "VOLTTRON_FAILED:" in stdout else stderr
            raise HTTPException(
                status_code=500,
                detail=f"VOLTTRON process failed to start. Log output:\n{log_output}"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected startup result. stdout: {stdout}\nstderr: {stderr}"
            )

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
        cmd = f'''
    VENV_PATH="{venv_path}"
    VOLTTRON_HOME="{volttron_home}"
    VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
    VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
    export VOLTTRON_HOME

    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
        exit 1
    fi
    source "$VENV_PATH/bin/activate"

    "$VENV_PATH/bin/vctl" shutdown --platform
    '''

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
    logger.info(f"[START_AGENT] Called with platform_id={platform_id}, agent_id={agent_id}")
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
        
        # Build command to start the agent (direct SSH, no ansible ad-hoc)
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"
        agent_id_arg = shlex.quote(agent_id)

        cmd = f'''
VENV_PATH="{venv_path}"
VOLTTRON_HOME="{volttron_home}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
export VOLTTRON_HOME

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
    exit 1
fi
source "$VENV_PATH/bin/activate"

"$VENV_PATH/bin/vctl" start {agent_id_arg}
'''

        logger.info(f"[START_AGENT] Executing start command for UUID {agent_id}")
        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)
        logger.info(f"[START_AGENT] Command completed: return_code={return_code}, stdout={stdout}, stderr={stderr}")

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

        cmd = f'''
VOLTTRON_HOME="{volttron_home}"
VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
tail -n {lines} "$VOLTTRON_HOME/volttron.log" || echo NO_LOG_FILE
'''

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=15)

        if "NO_LOG_FILE" in stdout:
            log_content = f"No log file detected at: {volttron_home}/volttron.log\n\nVOLTTRON may not have been started yet, or logging is not configured."
        else:
            log_content = stdout

        log_path = volttron_home.replace("~", "$HOME", 1) if volttron_home.startswith("~") else volttron_home
        return {
            "logs": log_content,
            "log_path": f"{log_path}/volttron.log",
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

        cmd = f'''
    VOLTTRON_HOME="{volttron_home}"
    VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
    rm -f "$VOLTTRON_HOME/volttron.log" && echo LOG_DELETED
    '''

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=10)
        
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
    logger.info(f"[STOP_AGENT] Called with platform_id={platform_id}, agent_id={agent_id}")
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
        
        # Build command to stop the agent (direct SSH, no ansible ad-hoc)
        # agent_id is now the UUID passed from the UI
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"
        agent_uuid_arg = shlex.quote(agent_id)

        cmd = f'''
VENV_PATH="{venv_path}"
VOLTTRON_HOME="{volttron_home}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
export VOLTTRON_HOME

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
    exit 1
fi
source "$VENV_PATH/bin/activate"

"$VENV_PATH/bin/vctl" stop {agent_uuid_arg}
'''

        logger.info(f"[STOP_AGENT] Executing stop command for UUID {agent_id}")
        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)
        logger.info(f"[STOP_AGENT] Command completed: return_code={return_code}, stdout={stdout[:200]}, stderr={stderr[:200]}")

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
    """Install an agent on a running VOLTTRON platform.

    For monolithic VOLTTRON: Uses vctl install with a path to the agent source.
    For modular VOLTTRON: Uses pip install with the package name.

    Args:
        platform_id: The platform instance name
        agent_identity: The VIP identity for the agent
        agent_source: For modular: pip package name (e.g., 'volttron-listener').
                      For monolithic: relative path in VOLTTRON source (e.g., 'examples/ListenerAgent')
                      or pip package name which will be resolved to monolithic path from catalog.
        start_agent: Whether to start the agent after installation (default: True)
        agent_config: Optional path to agent config file on remote system
    """
    logger.info(f"[INSTALL_AGENT] Called with platform_id={platform_id}, agent_identity={agent_identity}, agent_source={agent_source}, start_agent={start_agent}")
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

        # Get the VOLTTRON type to determine installation method
        volttron_type = platform.config.volttron_type
        agent_identity_arg = shlex.quote(agent_identity)

        # Get VOLTTRON source path for monolithic installations
        volttron_source = host.volttron_source if host.volttron_source else "~/volttron"

        # Determine the agent source based on VOLTTRON type
        pre_install_cmd = ""
        if volttron_type == "monolithic":
            # For monolithic VOLTTRON, agents are in the codebase
            # If agent_source looks like a pip package, resolve to monolithic path
            resolved_source = agent_source
            if agent_source.startswith("volttron-") or not ('/' in agent_source):
                # Looks like a pip package name, try to find monolithic source
                catalog = AgentCatalog()
                for agent_key, agent_type in catalog.agents.items():
                    if agent_type.source == agent_source and agent_type.monolithic_source:
                        resolved_source = agent_type.monolithic_source
                        logger.info(f"Resolved pip package {agent_source} to monolithic path {resolved_source}")
                        break

            # Build the agent path for monolithic
            if resolved_source.startswith('/') or resolved_source.startswith('~'):
                if resolved_source.startswith('~'):
                    agent_source_for_vctl = shlex.quote(resolved_source.replace("~", "$HOME", 1))
                else:
                    agent_source_for_vctl = shlex.quote(resolved_source)
            else:
                # Relative path - resolve from VOLTTRON source directory
                agent_source_for_vctl = f"$VOLTTRON_SOURCE/{resolved_source}"
        else:
            # For modular VOLTTRON, use the pip package name directly with vctl
            agent_source_for_vctl = shlex.quote(agent_source)
            # Ensure the package is installed first via pip for Modular VOLTTRON
            pre_install_cmd = f"pip install {agent_source_for_vctl}"

        # Build vctl install command (used for both modular and monolithic)
        vctl_install_cmd = f"\"$VENV_PATH/bin/vctl\" install {agent_source_for_vctl} --vip-identity {agent_identity_arg}"
        if start_agent:
            vctl_install_cmd += " --start"
        if agent_config:
            config_arg = shlex.quote(agent_config)
            vctl_install_cmd += f" --agent-config {config_arg}"

        cmd = f'''
VENV_PATH="{venv_path}"
VOLTTRON_HOME="{volttron_home}"
VOLTTRON_SOURCE="{volttron_source}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
VOLTTRON_SOURCE="${{VOLTTRON_SOURCE/#\~/$HOME}}"
export VOLTTRON_HOME

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
    exit 1
fi
source "$VENV_PATH/bin/activate"

{pre_install_cmd}
{vctl_install_cmd}
'''

        logger.info(f"[INSTALL_AGENT] Installing agent {agent_identity} on platform {platform_id}")
        logger.info(f"[INSTALL_AGENT] Full command: {cmd}")

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=600)
        logger.info(f"[INSTALL_AGENT] Command completed: return_code={return_code}")

        if return_code != 0:
            error_msg = stderr or stdout
            logger.error(f"Failed to install agent {agent_identity}: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to install agent {agent_identity}: {error_msg}"
            )

        logger.info(f"Agent {agent_identity} installed successfully on platform {platform_id} ({volttron_type})")
        return {
            "status": "success",
            "message": f"Agent {agent_identity} installed successfully ({volttron_type} mode)",
            "output": stdout,
            "agent_identity": agent_identity,
            "started": start_agent,
            "volttron_type": volttron_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing agent: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@ansible_router.get("/installed_driver_libraries/{platform_id}")
async def get_installed_driver_libraries(
    platform_id: str,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """List driver libraries currently installed in the VOLTTRON venv.

    Runs `pip list --format=json` and filters for packages matching known
    driver library prefixes (volttron-lib-*-driver).
    """
    logger.info(f"[INSTALLED_DRIVERS] Listing installed driver libraries for {platform_id}")
    try:
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)
        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()
        if platform.config.instance_name not in all_hosts:
            raise HTTPException(status_code=404, detail=f"Host entry for {platform.config.instance_name} not found")

        host = all_hosts[platform.config.instance_name]
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"

        cmd = f'''
VENV_PATH="{venv_path}"
VENV_PATH="${{VENV_PATH/#\\~/$HOME}}"

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
    exit 1
fi
source "$VENV_PATH/bin/activate"
pip list --format=json 2>/dev/null
'''

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=60)
        if return_code != 0:
            raise HTTPException(status_code=500, detail=f"pip list failed: {stderr or stdout}")

        import json as _json
        try:
            all_packages = _json.loads(stdout)
        except _json.JSONDecodeError:
            # stdout might contain extra lines before the JSON
            for line in stdout.strip().split("\n"):
                line = line.strip()
                if line.startswith("["):
                    all_packages = _json.loads(line)
                    break
            else:
                all_packages = []

        # Filter for driver libraries
        driver_packages = [
            pkg for pkg in all_packages
            if "driver" in pkg.get("name", "").lower()
            and pkg.get("name", "").lower().startswith("volttron-lib")
        ]

        return {"installed_drivers": driver_packages}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing installed driver libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ansible_router.post("/install_driver_library/{platform_id}")
async def install_driver_library(
    platform_id: str,
    pip_package: str,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Install a driver library (e.g. volttron-lib-fake-driver) into the VOLTTRON venv.

    Driver libraries are pip packages that the platform.driver agent uses to
    communicate with specific device protocols. They must be installed into the
    same venv as VOLTTRON before adding driver configurations.

    Args:
        platform_id: The platform instance name
        pip_package: The pip package name (e.g. 'volttron-lib-fake-driver')
    """
    logger.info(f"[INSTALL_DRIVER_LIB] Installing {pip_package} on platform {platform_id}")
    try:
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)

        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()

        if platform.config.instance_name not in all_hosts:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found"
            )

        host = all_hosts[platform.config.instance_name]
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        package_arg = shlex.quote(pip_package)

        cmd = f'''
VENV_PATH="{venv_path}"
VENV_PATH="${{VENV_PATH/#\\~/$HOME}}"

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
    exit 1
fi
source "$VENV_PATH/bin/activate"
pip install {package_arg}
'''

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=300)

        if return_code != 0:
            error_msg = stderr or stdout
            logger.error(f"Failed to install driver library {pip_package}: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to install {pip_package}: {error_msg}"
            )

        logger.info(f"Driver library {pip_package} installed successfully on platform {platform_id}")
        return {
            "status": "success",
            "message": f"Driver library {pip_package} installed successfully",
            "output": stdout,
            "package": pip_package,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing driver library: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ansible_router.post("/remove_agent/{platform_id}/{agent_uuid}")
async def remove_agent(
    platform_id: str,
    agent_uuid: str,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Remove/uninstall an agent from a running VOLTTRON platform using vctl remove.

    Args:
        platform_id: The platform instance name
        agent_uuid: The UUID of the agent to remove
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

        # Build command to remove the agent using UUID
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"
        agent_uuid_arg = shlex.quote(agent_uuid)

        cmd = f'''
VENV_PATH="{venv_path}"
VOLTTRON_HOME="{volttron_home}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
export VOLTTRON_HOME

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
    exit 1
fi
source "$VENV_PATH/bin/activate"

"$VENV_PATH/bin/vctl" remove {agent_uuid_arg}
'''

        logger.info(f"Removing agent UUID {agent_uuid} from platform {platform_id}")

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)

        if return_code != 0:
            error_msg = stderr or stdout
            logger.error(f"Failed to remove agent {agent_uuid}: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove agent {agent_uuid}: {error_msg}"
            )

        logger.info(f"Agent {agent_uuid} removed successfully from platform {platform_id}")
        return {
            "status": "success",
            "message": f"Agent removed successfully",
            "output": stdout,
            "agent_uuid": agent_uuid
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing agent: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@ansible_router.post("/platforms/{platform_id}/agents/{agent_identity}/deploy_config_store")
async def deploy_agent_config_store(
    platform_id: str,
    agent_identity: str,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Deploy agent config store entries to remote VOLTTRON platform.
    
    This function takes all config_store entries defined for an agent in the platform
    definition and deploys them to the running VOLTTRON instance using vctl config store commands.
    
    Args:
        platform_id: The platform instance name
        agent_identity: The VIP identity of the agent whose configs to deploy
    
    Returns:
        Status response with details about deployed configs
    """
    logger.info(f"[DEPLOY_CONFIG_STORE] Called for platform={platform_id}, agent={agent_identity}")
    
    try:
        # Get platform definition and host entry
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)

        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

        # Check if agent exists in platform definition
        if agent_identity not in platform.agents:
            raise HTTPException(
                status_code=404,
                detail=f"Agent {agent_identity} not found in platform definition"
            )

        agent = platform.agents[agent_identity]
        
        if not agent.config_store:
            return {
                "status": "success",
                "message": "No config store entries to deploy",
                "deployed_count": 0
            }

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
        agent_identity_arg = shlex.quote(agent_identity)

        deployed_configs = []
        failed_configs = []

        # Deploy each config store entry
        for config_name, config_entry in agent.config_store.items():
            try:
                logger.info(f"Deploying config: {config_name} (type: {config_entry.data_type})")
                
                # Sanitize config name for temp file
                safe_config_name = config_name.replace("/", "_").replace(" ", "_")
                temp_file = f"/tmp/volttron_config_{safe_config_name}_{os.urandom(4).hex()}"
                
                # Determine data type flag for vctl config store
                if config_entry.data_type == "CSV":
                    type_flag = "--csv"
                elif config_entry.data_type == "JSON":
                    type_flag = "--json"
                else:
                    type_flag = "--raw"
                config_name_arg = shlex.quote(config_name)
                
                # Use base64 encoding to transfer content safely
                # This avoids any shell escaping issues with heredocs
                import base64
                content_b64 = base64.b64encode(config_entry.value.encode("utf-8")).decode("ascii")
                
                cmd = f'''
VENV_PATH="{venv_path}"
VOLTTRON_HOME="{volttron_home}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
export VOLTTRON_HOME

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
    exit 1
fi

# Decode base64 config content to temp file
echo "{content_b64}" | base64 -d > {temp_file}

# Activate venv and deploy config
source "$VENV_PATH/bin/activate"
"$VENV_PATH/bin/vctl" config store {agent_identity_arg} {config_name_arg} {temp_file} {type_flag}
DEPLOY_RC=$?

# Clean up temp file
rm -f {temp_file}
exit $DEPLOY_RC
'''

                return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=60)

                if return_code != 0:
                    error_msg = stderr or stdout
                    logger.error(f"Failed to deploy config {config_name}: {error_msg}")
                    failed_configs.append({
                        "config_name": config_name,
                        "error": error_msg
                    })
                else:
                    logger.info(f"Successfully deployed config: {config_name}")
                    deployed_configs.append(config_name)
                    
            except Exception as e:
                logger.error(f"Exception deploying config {config_name}: {e}")
                failed_configs.append({
                    "config_name": config_name,
                    "error": str(e)
                })

        # Return summary
        result = {
            "status": "success" if not failed_configs else "partial",
            "message": f"Deployed {len(deployed_configs)}/{len(agent.config_store)} configs",
            "deployed_count": len(deployed_configs),
            "failed_count": len(failed_configs),
            "deployed_configs": deployed_configs,
            "failed_configs": failed_configs
        }

        if failed_configs and not deployed_configs:
            result["status"] = "failed"
            raise HTTPException(status_code=500, detail=result)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying config store: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@ansible_router.get("/platforms/{platform_id}/vctl_config_list")
async def vctl_config_list(
    platform_id: str,
    agent_identity: str = None,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Run vctl config list [agent_identity] on the VOLTTRON platform.

    Without agent_identity: returns list of agents that have config store entries.
    With agent_identity: returns list of config keys for that agent.
    """
    try:
        inventory_service = await get_inventory_service()
        all_hosts = await inventory_service.get_hosts()

        if platform_id not in all_hosts:
            raise HTTPException(status_code=404, detail=f"Host {platform_id} not found")

        host = all_hosts[platform_id]
        venv_path = host.volttron_venv if host.volttron_venv else "~/volttron.venv"
        volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"

        identity_arg = f" {shlex.quote(agent_identity)}" if agent_identity else ""

        cmd = f'''
VENV_PATH="{venv_path}"
VOLTTRON_HOME="{volttron_home}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
export VOLTTRON_HOME

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"
"$VENV_PATH/bin/vctl" config list{identity_arg}
'''

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=15)

        if return_code != 0:
            raise HTTPException(status_code=500, detail=stderr or stdout)

        entries = [line.strip() for line in stdout.splitlines() if line.strip()]
        return {"entries": entries}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running vctl config list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    """Retrieves the agent catalog — modular VOLTTRON agents only (those with a pip package source)."""
    try:
        catalog = AgentCatalog()
        return catalog.modular_agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@catalog_router.get("/agents/github", response_model=GitHubAgentsResponse)
async def get_github_agents() -> GitHubAgentsResponse:
    """Fetch modular VOLTTRON agents from the eclipse-volttron GitHub org.
    Falls back to the built-in modular catalog when offline."""
    try:
        agents, is_offline = await fetch_github_agents()
        if is_offline:
            catalog = AgentCatalog()
            fallback = list(catalog.modular_agents.values())
            return GitHubAgentsResponse(agents=fallback, offline=True)
        return GitHubAgentsResponse(agents=agents, offline=False)
    except Exception as e:
        logger.error(f"GitHub agent fetch error: {e}")
        catalog = AgentCatalog()
        fallback = list(catalog.modular_agents.values())
        return GitHubAgentsResponse(agents=fallback, offline=True)


@catalog_router.get("/agents/local", response_model=list[AgentType])
async def get_local_agents() -> list[AgentType]:
    """Scan the local workspace directory for custom agent directories."""
    try:
        settings = get_settings()
        return await scan_local_agents(settings.local_agents_dir)
    except Exception as e:
        logger.warning(f"Local agent scan failed: {e}")
        return []


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
