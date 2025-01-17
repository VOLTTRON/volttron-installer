from fastapi import APIRouter

import volttron_installer.backend.models as m
from .models import Inventory, CreateInventoryRequest, SuccessResponse, CreatePlatformRequest, PlatformDefinition
from .dependencies import read_inventory, write_inventory

platform_router = APIRouter(prefix="/platforms")
ansible_router = APIRouter(prefix="/ansible")
task_router = APIRouter(prefix="/task")

@ansible_router.get("/inventory", response_model=Inventory)
def get_inventory() -> Inventory:
    return read_inventory()

@ansible_router.post("/inventory")
def add_to_inventory(inventory_item: CreateInventoryRequest):
    inventory = read_inventory()
    inventory.inventory[inventory_item.id] = inventory_item
    write_inventory(inventory)
    return SuccessResponse()

@ansible_router.delete("/inventory/{id}")
def remove_from_inventory(id: str):
    inventory = read_inventory()
    inventory.inventory.pop(id, None)
    write_inventory(inventory)
    return SuccessResponse()

@platform_router.get("/")
def get_platforms():
    return {"platforms": []}

@platform_router.post("/")
def add_platform(platform: CreatePlatformRequest):
    return SuccessResponse()

@platform_router.post("/configure", )
def configure_platform(platform: m.ConfigurePlatformRequest):
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
