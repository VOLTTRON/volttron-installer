"""Platform router endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from volttron_installer.backend.services.ansible_service import AnsibleService, get_ansible_service
from volttron_installer.backend.services.inventory_service import InventoryService, get_inventory_service
from volttron_installer.backend.services.platform_service import PlatformService, get_platform_service
from loguru import logger

from ..models import (
    CreatePlatformRequest,
    SuccessResponse,
    PlatformDefinition,
    CreateAgentRequest,
    AgentDefinition,
)

from ._helpers import (
    DEPLOY_PROGRESS,
    _init_deploy_progress,
    _append_deploy_log,
    _set_deploy_step,
    _finalize_deploy_progress,
    _compute_effective_instance_paths,
    _resolve_platform_host,
    _validate_no_same_host_conflicts,
    _select_python_cmd_for_host,
    _deploy_modular_via_ssh,
    _parse_ansible_tasks,
    _parse_ansible_error,
)

platform_router = APIRouter(prefix="/platforms", tags=["platforms"])


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
        await _validate_no_same_host_conflicts(
            candidate_platform=platform_definition,
            candidate_host=host,
            inventory_service=inventory_service,
            platform_service=platform_service,
        )
        await platform_service.create_platform(platform_definition)
        ans = await get_ansible_service()
        #await ans.run_playbook("run_platforms",  platform.host_id)
        return SuccessResponse(object=platform_definition)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.put("/{id}")
async def update_platform(id: str, platform: CreatePlatformRequest):
    """Updates an existing platform"""
    try:
        platform_service = await get_platform_service()
        inventory_service = await get_inventory_service()
        # Preserve the existing deployed flag so saves don't reset it to False.
        existing = await platform_service.get_platform(id)
        existing_deployed = existing.deployed if existing is not None else False
        platform_definition = PlatformDefinition(host_id=platform.host_id,
                                                 config=platform.config,
                                                 agents=platform.agents,
                                                 deployed=platform.deployed if platform.deployed else existing_deployed)

        candidate_host = await _resolve_platform_host(inventory_service, platform_definition, id)
        if candidate_host is None:
            raise HTTPException(status_code=404, detail="Host not found")

        await _validate_no_same_host_conflicts(
            candidate_platform=platform_definition,
            candidate_host=candidate_host,
            inventory_service=inventory_service,
            platform_service=platform_service,
            ignore_instance_name=id,
        )

        await platform_service.update_platform(id, platform_definition)
        return SuccessResponse()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
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

    host = await _resolve_platform_host(inventory_service, platform, platform_id)
    if host is None:
        raise HTTPException(status_code=404, detail=f"Host {platform.config.instance_name} not found in inventory")

    venv_path, _ = _compute_effective_instance_paths(host, platform.config)

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

        host = await _resolve_platform_host(inventory_service, platform, platform_id)
        if host is None:
            raise HTTPException(status_code=404, detail=f"Host {platform.config.instance_name} not found in inventory")

        await _validate_no_same_host_conflicts(
            candidate_platform=platform,
            candidate_host=host,
            inventory_service=inventory_service,
            platform_service=platform_service,
            ignore_instance_name=platform_id,
        )

        effective_venv_path, effective_volttron_home = _compute_effective_instance_paths(host, platform.config)
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
                venv_path=effective_venv_path,
                volttron_home=effective_volttron_home,
                platform_id=platform_id,
                agents=platform.agents,
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
            _, volttron_home = _compute_effective_instance_paths(host, platform.config)
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