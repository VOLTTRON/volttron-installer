import httpx, asyncio
from typing import Any, Optional, TypeVar, Type, Union, List, Dict, Literal
from pydantic import BaseModel
from ..backend.models import AgentType, HostEntry, PlatformDefinition, \
    CreatePlatformRequest, CreateOrUpdateHostEntryRequest, ReachableResponse, \
    PlatformDeploymentStatus, CreateAgentRequest, ToolRequest, ToolStatusResponse, \
    BACnetReadDeviceAllRequest, BACnetDevice, BACnetReadPropertyRequest, BACnetScanResults, \
    BACnetWritePropertyRequest
from ..models import WindowsHostIPModel, LocalIPModel
from rxconfig import config

API_BASE_URL = f"{config.api_url}"
API_PREFIX = "/api"
ANSIBLE_PREFIX = f"{API_PREFIX}/ansible"
PLATFORMS_PREFIX = f"{API_PREFIX}/platforms"
HOSTS_PREFIX = f"{ANSIBLE_PREFIX}/hosts"
CATALOG_PREFIX = f"{API_PREFIX}/catalog"
TASK_PREFIX = f"{API_PREFIX}/task"
MANAGE_TOOLS_PREFIX = f"{API_PREFIX}/manage_tools"
TOOL_PROXY_PREFIX = f"{API_PREFIX}/tool_proxy"

TOOLS_PREFIX = f"{API_PREFIX}/tools"
BACNET_SCAN_TOOL_PREFIX = f"{TOOLS_PREFIX}/bacnet_scan_tool"
DEFAULT_TIMEOUT = 5.0  # 5 seconds timeout

T = TypeVar('T')

def with_model(model_class: Type[T], response_type: str = "single"):
    """
    Decorator to transform HTTP responses into model objects.
    
    Args:
        model_class: The model class to transform the response into (the return model of the original backend endpoint)
        response_type: One of "single", "list", or "dict"
    """
    def decorator(func):
        async def wrapper(*args, **kwargs) -> Union[T, List[T], Dict[str, T]]:
            response = await func(*args, **kwargs)
            data = response.json()
            
            if response_type == "single":
                return model_class(**data)
            elif response_type == "list":
                return [model_class(**item) for item in data]
            elif response_type == "dict":
                return {key: model_class(**value) for key, value in data.items()}
            else:
                raise ValueError(f"Invalid response type: {response_type}")
                
        return wrapper
    return decorator


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error ({status_code}): {detail}")

async def get_request(url: str, params: Optional[dict[str, Any]] = None, 
                      timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Send an async GET request to the specified URL with optional parameters."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise ApiError(408, f"Request timed out connecting to {url}")
        except httpx.HTTPStatusError as e:
            raise ApiError(e.response.status_code, e.response.text)
        except Exception as e:
            raise ApiError(500, str(e))

async def post_request(url: str, data: Optional[dict[str, Any]] = None, timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Send an async POST request to the specified URL with optional JSON data."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise ApiError(408, f"Request timed out connecting to {url}")
        except httpx.HTTPStatusError as e:
            raise ApiError(e.response.status_code, e.response.text)
        except Exception as e:
            raise ApiError(500, str(e))

async def put_request(url: str, data: Optional[dict[str, Any]] = None,
                     timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Send an async PUT request to the specified URL with optional JSON data."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            response = await client.put(url, json=data)
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise ApiError(408, f"Request timed out connecting to {url}")
        except httpx.HTTPStatusError as e:
            raise ApiError(e.response.status_code, e.response.text)
        except Exception as e:
            raise ApiError(500, str(e))

async def delete_request(url: str, params: Optional[dict[str, Any]] = None,
                        timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Send an async DELETE request to the specified URL with optional parameters."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            response = await client.delete(url, params=params)
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise ApiError(408, f"Request timed out connecting to {url}")
        except httpx.HTTPStatusError as e:
            raise ApiError(e.response.status_code, e.response.text)
        except Exception as e:
            raise ApiError(500, str(e))

async def proxy_request(
        url: str, 
        request_type: Literal["PUT", "POST", "GET", "DELETE", "OPTIONS", "PATCH"], 
        timeout: float = DEFAULT_TIMEOUT, 
        **kwargs
    ) -> httpx.Response:
    """Send an async request to the specified URL."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            response = await client.request(
                method=request_type,
                url=url, 
                **kwargs
            )
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise ApiError(408, f"Request timed out connecting to {url}")
        except httpx.HTTPStatusError as e:
            raise ApiError(e.response.status_code, e.response.text)
        except Exception as e:
            raise ApiError(500, str(e))

# Endpoints.
# GET requests
@with_model(HostEntry)
async def get_host(host_id: str) -> HostEntry:
    return await get_request(f"{API_BASE_URL}{HOSTS_PREFIX}/{host_id}")

@with_model(HostEntry, response_type="list")
async def get_hosts() -> list[HostEntry]:
    return await get_request(f"{API_BASE_URL}{HOSTS_PREFIX}")

@with_model(AgentType, response_type="dict")
async def get_agent_catalog() -> dict[str, AgentType]:
    return await get_request(f"{API_BASE_URL}{CATALOG_PREFIX}/agents")

@with_model(AgentType)
async def get_agent_from_catalog(agent_id: str) -> AgentType:
    return await get_request(f"{API_BASE_URL}{CATALOG_PREFIX}/agents/{agent_id}")

@with_model(PlatformDefinition, response_type="list")
async def get_all_platforms() -> list[PlatformDefinition]:
    return await get_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/")

@with_model(AgentType, response_type="dict")
async def get_agent_catalog() -> dict[str, AgentType]:
    return await get_request(f"{API_BASE_URL}{CATALOG_PREFIX}/agents")

@with_model(PlatformDefinition)
async def get_platform_by_id(platform_id: str) -> PlatformDefinition:
    return await get_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}")

@with_model(PlatformDeploymentStatus)
async def get_platform_status(platform_id: str) -> PlatformDeploymentStatus:
    return await get_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/status/{platform_id}")

@with_model(ReachableResponse)
async def ping_resolvable_host(host_id: str) -> ReachableResponse:
    """Ping a host to check if it is reachable."""
    return await get_request(f"{API_BASE_URL}{TASK_PREFIX}/ping/{host_id}")

@with_model(ToolStatusResponse)
async def tool_status(tool_name: str) -> ToolStatusResponse:
    """Get a tool's status."""
    return await get_request(f"{API_BASE_URL}{MANAGE_TOOLS_PREFIX}/tool_status/{tool_name}")

@with_model(LocalIPModel)
async def get_bacnet_local_ip(target_ip: str = None) -> LocalIPModel:
    """Get local IP address for BACnet communication."""
    params = {"target_ip": target_ip}
    return await proxy_request(f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/get_local_ip", "GET", params=params)

@with_model(WindowsHostIPModel)
async def get_windows_host_ip() -> WindowsHostIPModel:
    """Get Windows host IP address for WSL2 users."""
    return await proxy_request(f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/get_windows_host_ip", "GET")

async def get_tool_proxy(tool_name: str, path: str, **kwargs) -> httpx.Response:
    return await proxy_request(f"{API_BASE_URL}{TOOL_PROXY_PREFIX}/{tool_name}/{path}", "GET", **kwargs)

# PUT requests
async def update_platform(platform_id: str, platform: CreatePlatformRequest):
    await put_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}", data=platform.model_dump())

async def update_agent(platform_id: str, agent_id: str, agent: CreateAgentRequest):
    await put_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}/agents/{agent_id}", data=agent.model_dump())

async def put_tool_proxy(tool_name: str, path: str, **kwargs) -> httpx.Response:
    return await proxy_request(f"{API_BASE_URL}{TOOL_PROXY_PREFIX}/{tool_name}/{path}", "PUT", **kwargs)

# POST requests
async def start_bacnet_proxy(local_device_address: str = None) -> dict[str, str]:
    """Start BACnet proxy with optional local device address."""
    data = {"local_device_address": local_device_address} if local_device_address else {}
    response = await proxy_request(f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/start_proxy", "POST", params=data)
    return response.json()

@with_model(BACnetScanResults)
async def scan_bacnet_ip_range(network_str: str) -> BACnetScanResults:
    """Scan a BACnet IP range for devices."""
    return await proxy_request(
        f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/bacnet/scan_ip_range",
        "POST",
        timeout=15.0,
        params={"network_str": network_str}
    )

async def read_bacnet_property(request: BACnetReadPropertyRequest) -> dict[str, str]:
    """Read a property from a BACnet device."""
    response = await proxy_request(
        f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/read_property",
        "POST",
        json=request.model_dump()
    )
    return response.json()

async def write_bacnet_property(request: BACnetWritePropertyRequest) -> dict[str, str]:
    """Write a property to a BACnet device."""
    from loguru import logger
    logger.debug(request.model_dump())
    response = await proxy_request(
        f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/write_property",
        "POST",
        json=request.model_dump()
    )
    return response.json()

async def read_bacnet_device_all(request: BACnetReadDeviceAllRequest) -> dict:
    """Read all properties from a BACnet device."""
    try:
        response = await proxy_request(
            f"{API_BASE_URL}{TOOL_PROXY_PREFIX}/bacnet_scan_tool/bacnet/read_device_all",  # Note: changed to TOOL_PROXY_PREFIX
            "POST",
            json=request.model_dump()
        )
        return response.json()
    except ApiError as e:
        # Log error but provide a response that won't break client code
        print(f"Error in read_bacnet_device_all: {e}")
        return {"status": "error", "message": str(e), "properties": ""}

async def bacnet_who_is(device_instance_low: int, device_instance_high: int, dest: str) -> dict:
    """Send BACnet Who-Is request."""
    response = await proxy_request(
        f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/bacnet/who_is",
        "POST",
        params={
            "device_instance_low": device_instance_low,
            "device_instance_high": device_instance_high,
            "dest": dest
        }
    )
    return response.json()

async def stop_bacnet_proxy() -> dict[str, str]:
    """Stop the BACnet proxy."""
    response = await proxy_request(f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/stop_proxy", "POST")
    return response.json()

async def create_platform(platform: CreatePlatformRequest):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/", data=platform.model_dump())

async def deploy_platform(platform_id: str):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/deploy/{platform_id}")

async def add_host(host: CreateOrUpdateHostEntryRequest):
    await post_request(f"{API_BASE_URL}{HOSTS_PREFIX}", data=host.model_dump())

async def start_platform(platform_id: str):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/start_platform", data=platform_id)

async def stop_platform(platform_id: str):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/stop_platform", data=platform_id)

async def create_agent(platform_id: str, agent: CreateAgentRequest):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}/agents", data=agent.model_dump())

async def start_tool(tool_request: ToolRequest):
    """Start a tool with the given request."""
    await post_request(f"{API_BASE_URL}{MANAGE_TOOLS_PREFIX}/start_tool", data=tool_request.model_dump())

async def stop_tool(tool_name: str):
    """Stop a tool by its name."""
    await post_request(f"{API_BASE_URL}{MANAGE_TOOLS_PREFIX}/stop_tool/{tool_name}")

async def post_tool_proxy(tool_name: str, path: str, **kwargs) -> httpx.Response:
    return await proxy_request(f"{API_BASE_URL}{TOOL_PROXY_PREFIX}/{tool_name}/{path}", "POST", **kwargs)

# DELETE requests
async def delete_platform(platform_id: str):
    await delete_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}")

async def remove_from_inventory(host_id: str):
    await delete_request(f"{API_BASE_URL}{HOSTS_PREFIX}/{host_id}")

async def delete_agent(platform_id: str, agent_id: str):
    await delete_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}/agents/{agent_id}")

async def delete_tool_proxy(tool_name: str, path: str, **kwargs) -> httpx.Response:
    await delete_request(f"{API_BASE_URL}/{TOOL_PROXY_PREFIX}/{tool_name}/{path}", "DELETE", **kwargs)
