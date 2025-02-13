from fastapi import APIRouter, HTTPException
from typing import Optional
import json
from pathlib import Path

from .models import (
    Inventory,
    CreateInventoryRequest,
    SuccessResponse,
    CreatePlatformRequest,
    PlatformDefinition,
    InventoryItem,
    ConfigurePlatformRequest
)
from .dependencies import read_inventory, write_inventory
from .services.ansible_service import AnsibleService

platform_router = APIRouter(prefix="/platforms")
ansible_router = APIRouter(prefix="/ansible")
task_router = APIRouter(prefix="/task")

# Create service instance at module level
ansible_service = AnsibleService()

@ansible_router.get("/inventory", response_model=Inventory)
def get_inventory() -> Inventory:
    try:
        return read_inventory()
    except Exception as e:
        # Return empty inventory on any error
        return Inventory(inventory={})

@ansible_router.post("/inventory")
def add_to_inventory(inventory_item: CreateInventoryRequest):
    try:
        # Create InventoryItem first to validate
        item = InventoryItem(
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
        if id in inventory.inventory:
            # Create new inventory without the item to delete
            new_inventory = Inventory(inventory={
                k: v for k, v in inventory.inventory.items() if k != id
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
async def deploy_platform(platform_config: dict):
    """Deploy a VOLTTRON platform using Ansible"""
    try:
        return_code, stdout, stderr = await ansible_service.run_playbook(
            "volttron.deployment.configure_platform",
            extra_vars=platform_config
        )

        if return_code != 0:
            raise HTTPException(status_code=500, detail=f"Ansible deployment failed: {stderr}")

        return {"message": "Platform deployed successfully", "output": stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@ansible_router.post("/ansible/start_platform")
async def start_platform(platform_id: str):
    """Start a VOLTTRON platform"""
    try:
        return_code, stdout, stderr = await ansible_service.run_ad_hoc(
            "volttron -vv -l volttron.log&"
        )

        if return_code != 0:
            raise HTTPException(status_code=500, detail=f"Failed to start platform: {stderr}")

        return {"message": "Platform started successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@ansible_router.post("/ansible/stop_platform")
async def stop_platform(platform_id: str):
    """Stop a VOLTTRON platform"""
    try:
        return_code, stdout, stderr = await ansible_service.run_ad_hoc(
            "vctl shutdown --platform"
        )

        if return_code != 0:
            raise HTTPException(status_code=500, detail=f"Failed to stop platform: {stderr}")

        return {"message": "Platform stopped successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
