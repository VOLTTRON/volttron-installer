from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
import json
from pathlib import Path
import os, asyncio

from volttron_installer.backend.tool_manager import ToolManager
from volttron_installer.backend.services.ansible_service import AnsibleService, get_ansible_service
from volttron_installer.backend.services.inventory_service import InventoryService, get_inventory_service
from volttron_installer.backend.services.platform_service import PlatformService, get_platform_service
from volttron_installer.backend.models import AgentCatalog

from volttron_installer.backend.tool_proxy_factory import ToolProxyFactory


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
bacnet_scan_tool_router = APIRouter(prefix=f"{TOOLS_PREFIX}/bacnet_scan_tool", tags=["bacnet scan tool"])

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
            host_configs_dir=host_entry.host_configs_dir
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
async def deploy_platform(platform_id: str,
                          ansible: AnsibleService = Depends(get_ansible_service),
                          platform_service: PlatformService = Depends(get_platform_service)):

    """Deploys a platform using Ansible"""
    try:
        platform_service = await get_platform_service()
        platform = await platform_service.get_platform(platform_id)
        if platform is None:
            raise HTTPException(status_code=404, detail="Platform not found")

        return_code, stdout, stderr = await ansible.run_playbook(
            "install-platform",
            hosts=platform.host_id,
            extra_vars=platform.config.model_dump()
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

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
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
    port = ToolManager.get_tool_port(tool_name) if is_running else None
    
    return ToolStatusResponse(**{
        "tool_name": tool_name,
        "running": is_running,
        "port": port
    })



@bacnet_scan_tool_router.get("/get_local_ip", response_model=dict[str, str])
async def bacnet_scan_get_local_ip(target_ip: str = None) -> dict[str, str]:
    # OPTIONAL
    from .tool_proxy_factory import ApiError

    url=f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/tool_proxy/bacnet_scan_tool/get_local_ip"
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

@bacnet_scan_tool_router.post("/start_proxy", response_model=dict[str, str])
async def bacnet_scan_start_proxy(local_device_address: str | None = None) -> dict[str, str]:
    from .tool_proxy_factory import ApiError

    url=f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/tool_proxy/bacnet_scan_tool/start_proxy"
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

@bacnet_scan_tool_router.get("/get_windows_host_ip", response_model=dict[str, str])
async def bacnet_scan_get_windows_host_ip() -> dict[str, str]:
    # OPTIONAL, for WSL2 users
    from .tool_proxy_factory import ApiError

    url=f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/tool_proxy/bacnet_scan_tool/get_windows_host_ip"
    try:
        response = await ToolProxyFactory.request(
            url,
            "GET",
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
@bacnet_scan_tool_router.post("/bacnet/scan_ip_range", response_model=BACnetScanResults)
async def bacnet_scan_scan_ip_range(network_str: str) -> dict[str, str]:
    from .tool_proxy_factory import ApiError

    url=f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/tool_proxy/bacnet_scan_tool/bacnet/scan_ip_range"
    REQUEST={"network_str": network_str}
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST
        )
        data = response.json()
        return BACnetScanResults(
            status=data["status"],
            devices=[
                BACnetDevice(
                    pduSource=device["pduSource"],
                    deviceIdentifier=device["deviceIdentifier"],
                    maxAPDULengthAccepted=device["maxAPDULengthAccepted"],
                    segmentationSupported=device["segmentationSupported"],
                    vendorID=device["vendorID"],
                    object_name=device["object-name"],
                    scanned_ip_target=device["scanned_ip_target"],
                    device_instance=device["device_instance"]
                ) for device in data["devices"]
            ]
        )
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
@bacnet_scan_tool_router.post("/read_property", response_model=dict[str, str])
async def bacnet_scan_read_property(request: BACnetReadPropertyRequest) -> dict[str, str]:
    from .tool_proxy_factory import ApiError

    url=f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/tool_proxy/bacnet_scan_tool/read_property"
    REQUEST = {
            "device_address": request.device_address,
            "object_identifier": request.object_identifier,
            "property_identifier": request.property_identifier,
            "property_array_index": request.property_array_index
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

@bacnet_scan_tool_router.post("/write_property", response_model=dict[str, str])
async def bacnet_scan_write_property(request: BACnetWritePropertyRequest) -> dict[str, str]:
    from .tool_proxy_factory import ApiError

    url=f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/tool_proxy/bacnet_scan_tool/write_property"
    REQUEST = {
            "device_address": request.device_address,
            "object_identifier": request.object_identifier,
            "property_identifier": request.property_identifier,
            "value": request.value,
            "priority": request.priority,
            "property_array_index": request.property_array_index
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

@bacnet_scan_tool_router.post("/bacnet/read_device_all")
async def bacnet_scan_read_device_all(request: BACnetReadDeviceAllRequest) -> dict[str, str]:
    from .tool_proxy_factory import ApiError

    url=f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/tool_proxy/bacnet_scan_tool/bacnet/read_device_all"
    REQUEST={
        "device_address": request.device_address,
        "device_object_identifier": request.device_object_identifier
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

@bacnet_scan_tool_router.post("/bacnet/who_is")
async def bacnet_scan_who_is(
        device_instance_low: int,
        device_instance_high: int,
        dest: str
    ) -> dict[str, str]:
    from .tool_proxy_factory import ApiError

    url=f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/tool_proxy/bacnet_scan_tool/bacnet/who_is"
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

@bacnet_scan_tool_router.post("/stop_proxy", response_model=dict[str, str])
async def bacnet_scan_stop_proxy() -> dict[str, str]:
    from .tool_proxy_factory import ApiError

    url=f"{os.environ.get('API_URL', 'http://localhost:8000')}/api/tool_proxy/bacnet_scan_tool/stop_proxy"
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    