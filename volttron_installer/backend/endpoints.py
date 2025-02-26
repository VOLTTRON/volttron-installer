from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import json
from pathlib import Path
import os

from volttron_installer.backend.services.ansible_service import AnsibleService, get_ansible_service
from volttron_installer.backend.services.inventory_service import get_inventory_service
from volttron_installer.backend.services.platform_service import get_platform_service

from .models import (
    CreateOrUpdateHostEntryRequest,
    SuccessResponse,
    CreatePlatformRequest,
    PlatformDefinition,
    HostEntry,
    ConfigurePlatformRequest,
    PlatformConfig
)


platform_router = APIRouter(prefix="/platforms", tags=["platforms"])
ansible_router = APIRouter(prefix="/ansible", tags=["ansible"])
task_router = APIRouter(prefix="/task", tags=["tasks"])


@ansible_router.get("/hosts", response_model=list[HostEntry])
async def get_hosts() -> list[HostEntry]:
    """Retrieves the inventory"""
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
            host_configs_dir=host_entry.host_configs_dir
        )

        inventory_service = await get_inventory_service()
        await inventory_service.add_host(item)
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
async def get_platforms():
    """Retrieves all platforms"""
    return {"platforms": []}

@platform_router.post("/")
async def create_platform(platform: CreatePlatformRequest):
    """Creates a new platform"""
    try:
        platform_service = await get_platform_service()
        platform_definition = PlatformDefinition(config=platform.config,
                                                 agents=platform.agents)
        await platform_service.add_platform(platform_definition)
        return SuccessResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@platform_router.post("/")
async def add_platform(platform: CreatePlatformRequest):
    """Adds a new platform"""
    return SuccessResponse()

@platform_router.post("/configure")
async def configure_platform(platform: ConfigurePlatformRequest):
    """Configures a platform"""
    # Get the platform definition
    # Configure the host installing dependent libraries
    # TODO: Implement this
    # ansible-playbook -K \
    #                  -i <path/to/your/inventory>.yml \
    #                  volttron.deployment.host_config
    return SuccessResponse()

@platform_router.post("/deploy")
async def deploy_platform(deploy):
    """Deploys a platform"""
    # Get the platform definition
    # Deploy the platform
    return SuccessResponse()

async def deploy_platforms():
    """Deploy all the platforms"""
    return SuccessResponse()

@platform_router.post("/{id}/run")
async def run_platform(id: str):
    """Runs a specific platform"""
    # TODO: Implement this
    # ansible-playbook -i <path/to/your/inventory>.yml \
    #              volttron.deployment.run_platforms
    return SuccessResponse()

@platform_router.post("/run")
async def run_platforms():
    """Runs all platforms"""
    return SuccessResponse()

@platform_router.post("/{id}/configure_agents")
async def configure_agents(id: str):
    """Configures agents for a platform"""
    # Get the platform definition
    # Configure the agents
    return SuccessResponse()

@platform_router.get("/status")
async def get_platforms_status():
    """Retrieves the status of all platforms"""
    return {"status": "ok"}

@platform_router.get("/{id}/status")
async def get_platform_status(id: str):
    """Retrieves the status of a specific platform"""
    return {"status": "ok"}

@platform_router.get("/{id}/agents")
async def get_agents_running_state(id: str):
    """Retrieves the running state of agents for a platform"""
    # ansible-playbook -i <path/to/your/inventory>.yml \
    #             volttron.deployment.ad_hoc -e "command='vctl status'"
    return {"agents": []}

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

@ansible_router.post("/ansible/deploy_platform")
async def deploy_platform(config: PlatformConfig, ansible: AnsibleService = Depends(get_ansible_service)):
    """Deploys a platform using Ansible"""
    try:
        return_code, stdout, stderr = await ansible.run_playbook(
            "install-platform",  # Updated playbook name
            extra_vars=config.model_dump()
        )

        if return_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Ansible deployment failed: {stderr or stdout}"
            )
        return {"status": "success", "output": stdout}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@ansible_router.post("/ansible/start_platform")
async def start_platform(platform_id: str, ansible: AnsibleService = Depends(get_ansible_service)):
    """Starts a platform using Ansible"""
    try:
        return_code, stdout, stderr = await ansible.run_volttron_ad_hoc(
            f"cd {platform_id} && ./start-volttron"
        )

        if return_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start platform: {stderr or stdout}"
            )
        return {"status": "success", "output": stdout}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@ansible_router.post("/ansible/stop_platform")
async def stop_platform(platform_id: str, ansible: AnsibleService = Depends(get_ansible_service)):
    """Stops a platform using Ansible"""
    try:
        return_code, stdout, stderr = await ansible.run_volttron_ad_hoc(
            f"cd {platform_id} && ./stop-volttron"
        )

        if return_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to stop platform: {stderr or stdout}"
            )
        return {"status": "success", "output": stdout}

    except Exception as e:
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

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
