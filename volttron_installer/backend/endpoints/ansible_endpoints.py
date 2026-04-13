"""Ansible router endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Request
import os, shlex, re
import asyncio
from loguru import logger

from volttron_installer.backend.services.ansible_service import AnsibleService, get_ansible_service
from volttron_installer.backend.services.inventory_service import InventoryService, get_inventory_service
from volttron_installer.backend.services.platform_service import PlatformService, get_platform_service

from ..models import (
    CreateOrUpdateHostEntryRequest,
    SuccessResponse,
    HostEntry,
    AgentCatalog,
)

from ._helpers import (
    _compute_effective_instance_paths,
    _resolve_platform_host,
    _resolve_platform_host_and_paths,
    _extract_github_repo,
    _extract_subdirectory_from_source,
    _github_repo_has_python_project,
)

ansible_router = APIRouter(prefix="/ansible", tags=["ansible"])


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


@ansible_router.post("/start_platform/{platform_id}")
async def start_platform(platform_id: str, ansible: AnsibleService = Depends(get_ansible_service)):
    """Starts a VOLTTRON platform using vctl"""
    try:
        # Get platform definition and host entry
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)

        if platform is None:
            raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

        inventory_service = await get_inventory_service()
        host = await _resolve_platform_host(inventory_service, platform, platform_id)
        if host is None:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )

        # Build paths
        venv_path, volttron_home = _compute_effective_instance_paths(host, platform.config)

        # First check if VOLTTRON is already running using vctl status (authoritative check)
        check_cmd = f"export VOLTTRON_HOME={volttron_home} && source {venv_path}/bin/activate && vctl status > /dev/null 2>&1 && echo RUNNING || echo STOPPED"
        check_code, check_stdout, _ = await ansible.run_ssh_command(host, check_cmd, timeout=15)

        if "RUNNING" in check_stdout and "STOPPED" not in check_stdout:
            return {"status": "success", "message": "VOLTTRON is already running.", "already_running": True}

        # Clean up config file - remove installer-only fields that VOLTTRON doesn't recognize
        # Remove: instance-name, instance_name, messagebus, message_bus, options, vip_address, volttron_type (installer-only)
        # Also disable agent-isolation-mode which causes poetry issues
        cleanup_cmd = f"sed -i '/instance.name/d; /instance_name/d; /^messagebus/d; /message_bus/d; /^options/d; /vip_address/d; /volttron_type/d; s/agent-isolation-mode = True/agent-isolation-mode = False/g' {volttron_home}/config 2>/dev/null || true"
        await ansible.run_ssh_command(host, cleanup_cmd, timeout=10)

        # SSH startup: activate venv, set VOLTTRON_HOME, start in background
        # Use nohup so the process survives the SSH session ending.
        # Poll vctl status until platform reports running (up to 30s).
        venv_bin = venv_path.replace("~", "$HOME")
        vhome = volttron_home.replace("~", "$HOME")
        startup_cmd = f'''
VENV_BIN="{venv_bin}"
VHOME="{vhome}"
export VOLTTRON_HOME="$VHOME"
export PATH="$VENV_BIN/bin:$PATH"

if [ ! -f "$VENV_BIN/bin/activate" ]; then
    echo "VOLTTRON_FAILED: venv not found at $VENV_BIN"
    exit 1
fi
. "$VENV_BIN/bin/activate"
mkdir -p "$VHOME"

nohup env VOLTTRON_HOME="$VHOME" PATH="$VENV_BIN/bin:$PATH" volttron -vv -l "$VHOME/volttron.log" </dev/null &>/dev/null &
disown

# Poll until platform is running (max 30 seconds)
for i in $(seq 1 30); do
  sleep 1
  if "$VENV_BIN/bin/vctl" status >/dev/null 2>&1; then
    echo "VOLTTRON_RUNNING"
    exit 0
  fi
done
echo "VOLTTRON_STARTED_BUT_NOT_CONFIRMED"
'''

        logger.info(f"[START] Starting VOLTTRON via direct SSH for platform {platform_id}")
        return_code, stdout, stderr = await ansible.run_ssh_command(host, startup_cmd, timeout=60)

        logger.debug(f"Startup result - return_code: {return_code}, stdout: {stdout[:500]}, stderr: {stderr[:500]}")

        if "VOLTTRON_RUNNING" in stdout:
            return {"status": "success", "message": "Platform started and confirmed running."}
        elif "VOLTTRON_STARTED_BUT_NOT_CONFIRMED" in stdout:
            return {"status": "success", "message": "Platform start command issued, but platform did not confirm running within 30 seconds."}
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

        inventory_service = await get_inventory_service()
        host = await _resolve_platform_host(inventory_service, platform, platform_id)
        if host is None:
            raise HTTPException(
                status_code=404,
                detail=f"Host entry for {platform.config.instance_name} not found in inventory"
            )

        # Build paths
        venv_path, volttron_home = _compute_effective_instance_paths(host, platform.config)

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
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

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
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

        # Build command to start the agent (direct SSH, no ansible ad-hoc)
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
        ansible = await get_ansible_service()
        inventory_service = await get_inventory_service()
        _, host, _, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

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
        ansible = await get_ansible_service()
        inventory_service = await get_inventory_service()
        _, host, _, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

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
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

        # Build command to stop the agent (direct SSH, no ansible ad-hoc)
        # agent_id is now the UUID passed from the UI
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
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        platform, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

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
        inventory_service = await get_inventory_service()
        _, host, venv_path, _ = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

        venv_bin = venv_path.replace("~", "$HOME")
        cmd = f'"{venv_bin}/bin/pip" list --format=json 2>/dev/null'

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
        github_repo = _extract_github_repo(pip_package)
        if github_repo is not None:
            owner, repo = github_repo
            subdirectory = _extract_subdirectory_from_source(pip_package)
            is_valid, reason = _github_repo_has_python_project(owner, repo, subdirectory)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Source '{pip_package}' is not installable: {reason} "
                        "If your package lives in a nested folder, use: "
                        "git+https://github.com/<owner>/<repo>.git#subdirectory=<path>."
                    ),
                )

        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )
        package_arg = shlex.quote(pip_package)

        venv_bin = venv_path.replace("~", "$HOME")
        vhome = volttron_home.replace("~", "$HOME")
        cmd = f'VOLTTRON_HOME="{vhome}" "{venv_bin}/bin/vctl" install-lib {package_arg}'

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
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

        # Build command to remove the agent using UUID
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

        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

        # Build paths
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
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

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


@ansible_router.get("/platforms/{platform_id}/vctl_config_get")
async def vctl_config_get(
    platform_id: str,
    agent_identity: str,
    config_key: str,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Run vctl config get <agent_identity> <config_key> on the VOLTTRON platform."""
    try:
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

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
"$VENV_PATH/bin/vctl" config get {shlex.quote(agent_identity)} {shlex.quote(config_key)}
'''

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=15)

        if return_code != 0:
            raise HTTPException(status_code=500, detail=stderr or stdout)

        return {"content": stdout.strip()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running vctl config get: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ansible_router.delete("/platforms/{platform_id}/vctl_config_delete")
async def vctl_config_delete(
    platform_id: str,
    agent_identity: str,
    config_key: str,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Run vctl config delete <agent_identity> <config_key> on the VOLTTRON platform."""
    try:
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

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
"$VENV_PATH/bin/vctl" config delete {shlex.quote(agent_identity)} {shlex.quote(config_key)}
'''

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=15)

        if return_code != 0:
            raise HTTPException(status_code=500, detail=stderr or stdout)

        return {"status": "deleted", "config_key": config_key}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running vctl config delete: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ansible_router.post("/platforms/{platform_id}/vctl_config_store")
async def vctl_config_store(
    platform_id: str,
    agent_identity: str,
    config_key: str,
    request: Request,
    ansible: AnsibleService = Depends(get_ansible_service)
):
    """Run vctl config store <agent_identity> <config_key> with raw text content."""
    try:
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        _, host, venv_path, volttron_home = await _resolve_platform_host_and_paths(
            platform_id,
            inventory_service,
            platform_service,
        )

        body = await request.json()
        content = body.get("content", "")

        # Determine config type flag.
        # vctl config get always returns data as JSON (even for CSV configs), so when the
        # round-tripped content is valid JSON we must use --json, not --csv.
        # Only fall back to --csv if the content is plaintext CSV (no leading [ or {).
        import json as _json
        try:
            _json.loads(content.strip())
            config_flag = "--json"
        except (ValueError, _json.JSONDecodeError):
            config_flag = "--csv" if config_key.endswith(".csv") else "--json"

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
cat <<'__VCTL_EOF__' | "$VENV_PATH/bin/vctl" config store {shlex.quote(agent_identity)} {shlex.quote(config_key)} {config_flag}
{content}
__VCTL_EOF__
'''

        return_code, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=20)

        if return_code != 0:
            raise HTTPException(status_code=500, detail=stderr or stdout)

        return {"status": "stored", "config_key": config_key}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running vctl config store: {e}")
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
        from ..models import HostEntry
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