from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import json
from pathlib import Path
import os

from .models import (
    Inventory,
    CreateInventoryRequest,
    SuccessResponse,
    CreatePlatformRequest,
    PlatformDefinition,
    HostEntry,
    ConfigurePlatformRequest,
    PlatformConfig
)
from .dependencies import read_inventory, write_inventory
from .services.ansible_service import AnsibleService

platform_router = APIRouter(prefix="/platforms")
ansible_router = APIRouter(prefix="/ansible")
task_router = APIRouter(prefix="/task")

# Make sure we're using a single instance of AnsibleService
_ansible_service = None

def get_ansible_service():
    global _ansible_service
    if _ansible_service is None:
        _ansible_service = AnsibleService()
    return _ansible_service

@ansible_router.get("/inventory", response_model=Inventory)
def get_inventory() -> Inventory:
    try:
        return read_inventory()
    except Exception as e:
        # Return empty inventory on any error
        return Inventory(inventory={})

@ansible_router.get("/inventory/{id}", response_model=HostEntry)
def get_host_entry_by_id(id: str) -> HostEntry:
    try:
        inventory = read_inventory()
        if id in inventory.host_entries:
            return inventory.host_entries.get(id)
    except Exception as e:  
        # Return empty inventory on any error
        return Inventory(inventory={})

@ansible_router.post("/inventory")
def add_to_inventory(inventory_item: CreateInventoryRequest):
    try:
        # Create HostEntry first to validate
        item = HostEntry(
            id=inventory_item.id,
            ansible_user=inventory_item.ansible_user,
            ansible_host=inventory_item.ansible_host,
            ansible_port=inventory_item.ansible_port,
            http_proxy=inventory_item.http_proxy,
            https_proxy=inventory_item.https_proxy,
            volttron_venv=inventory_item.volttron_venv,
            host_configs_dir=inventory_item.host_configs_dir
        )

        # Create new inventory with just this item
        new_inventory = Inventory(inventory={item.id: item})
        write_inventory(new_inventory, merge=True)  # Explicitly set merge=True
        return SuccessResponse()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@ansible_router.delete("/inventory/{id}")
def remove_from_inventory(id: str):
    try:
        inventory = read_inventory()
        if id in inventory.host_entries:
            # Create new inventory without the item to delete
            new_inventory = Inventory(inventory={
                k: v for k, v in inventory.host_entries.items() if k != id
            })
            # Overwrite the entire inventory
            write_inventory(new_inventory, merge=False)
        return SuccessResponse()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@platform_router.get("/")
def get_platforms():
    return {"platforms": []}

@platform_router.post("/")
def add_platform(platform: CreatePlatformRequest):
    return SuccessResponse()

@platform_router.post("/configure")
def configure_platform(platform: ConfigurePlatformRequest):
    # Get the platform definition
    # Configure the host installing dependent libaries
    # TODO: Implement this
    # ansible-playbook -K \
    #                  -i <path/to/your/inventory>.yml \
    #                  volttron.deployment.host_config
    return SuccessResponse()

@platform_router.post("/deploy")
def deploy_platform(deploy):
    # Get the platform definition
    # Deploy the platform
    return SuccessResponse()


def deploy_platforms():
    # Deploy all the platforms
    return SuccessResponse()

@platform_router.post("/{id}/run")
def run_platform(id: str):
    # TODO: Implement this
    # ansible-playbook -i <path/to/your/inventory>.yml \
    #              volttron.deployment.run_platforms
    return SuccessResponse()

@platform_router.post("/run")
def run_platforms():
    # Run all the platforms
    return SuccessResponse()

@platform_router.post("/{id}/configure_agents")
def configure_agents(id: str):
    # Get the platform definition
    # Configure the agents
    return SuccessResponse()

@platform_router.get("/status")
def get_platforms_status():
    return {"status": "ok"}


@platform_router.get("/{id}/status")
def get_platform_status(id: str):
    return {"status": "ok"}

@platform_router.get("/{id}/agents")
def get_agents_running_state(id: str):
    # ansible-playbook -i <path/to/your/inventory>.yml \
    #             volttron.deployment.ad_hoc -e "command='vctl status'"
    return {"agents": []}

@task_router.get("/")
def get_tasks():
    # Get the list of tasks
    return {"tasks": []}

@task_router.get("/{id}")
def task_status(id: str):
    # Get the status of the task
    return {"status": "ok"}

@ansible_router.post("/ansible/deploy_platform")
async def deploy_platform(config: PlatformConfig, ansible: AnsibleService = Depends(get_ansible_service)):
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
    try:
        return_code, stdout, stderr = await ansible.run_ad_hoc(
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
    try:
        return_code, stdout, stderr = await ansible.run_ad_hoc(
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
