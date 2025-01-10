from fastapi import APIRouter

import volttron_installer.backend.models as m
from .models import Inventory, InventoryRequest, SuccessResponse, CreatePlatformRequest, PlatformDefinition
from .dependencies import read_inventory, write_inventory

platform_router = APIRouter(prefix="/platforms")
ansible_router = APIRouter(prefix="/ansible")
task_router = APIRouter(prefix="/task")

@ansible_router.get("/inventory", response_model=Inventory)
async def get_inventory() -> Inventory:
    return read_inventory()

@ansible_router.post("/inventory")
async def add_to_inventory(inventory_item: InventoryRequest):
    inventory = read_inventory()
    inventory.inventory[inventory_item.id] = inventory_item
    write_inventory(inventory)
    return SuccessResponse()

@ansible_router.delete("/inventory/{id}")
async def remove_from_inventory(id: str):
    inventory = read_inventory()
    inventory.inventory.pop(id, None)
    write_inventory(inventory)
    return SuccessResponse()

@platform_router.get("/")
async def get_platforms():
    return {"platforms": []}

@platform_router.post("/")
async def add_platform(platform: CreatePlatformRequest):
    return SuccessResponse()

@platform_router.post("/configure", )
async def configure_platform(platform: m.ConfigurePlatformRequest):
    # Get the platform definition
    # Configure the host installing dependent libaries
    # TODO: Implement this
    # ansible-playbook -K \
    #                  -i <path/to/your/inventory>.yml \
    #                  volttron.deployment.host_config
    return SuccessResponse()

@platform_router.post("/deploy")
async def deploy_platform(deploy):
    # Get the platform definition
    # Deploy the platform
    return SuccessResponse()


async def deploy_platforms():
    # Deploy all the platforms
    return SuccessResponse()

@platform_router.post("/{id}/run")
async def run_platform(id: str):
    # TODO: Implement this
    # ansible-playbook -i <path/to/your/inventory>.yml \
    #              volttron.deployment.run_platforms
    return SuccessResponse()

@platform_router.post("/run")
async def run_platforms():
    # Run all the platforms
    return SuccessResponse()

@platform_router.post("/{id}/configure_agents")
async def configure_agents(id: str):
    # Get the platform definition
    # Configure the agents
    return SuccessResponse()

@platform_router.get("/status")
async def get_platforms_status():
    return {"status": "ok"}


@platform_router.get("/{id}/status")
async def get_platform_status(id: str):
    return {"status": "ok"}

@platform_router.get("/{id}/agents")
async def get_agents_running_state(id: str):
    # ansible-playbook -i <path/to/your/inventory>.yml \
    #             volttron.deployment.ad_hoc -e "command='vctl status'"
    return {"agents": []}

@task_router.get("/")
async def get_tasks():
    # Get the list of tasks
    return {"tasks": []}

@task_router.get("/{id}")
async def task_status(id: str):
    # Get the status of the task
    return {"status": "ok"}
