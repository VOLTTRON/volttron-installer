import httpx, asyncio
from typing import Any, Optional, TypeVar, Type, Union, List, Dict, Literal
from pydantic import BaseModel
from ..backend.models import AgentType, HostEntry, PlatformDefinition, \
    CreatePlatformRequest, CreateOrUpdateHostEntryRequest, ReachableResponse, \
    PlatformDeploymentStatus, CreateAgentRequest, ToolRequest, ToolStatusResponse, \
    BACnetReadDeviceAllRequest, BACnetDevice, BACnetReadPropertyRequest, BACnetScanResults, \
    BACnetWritePropertyRequest, BACnetReadObjectListRequest
from ..models import WindowsHostIPModel, LocalIPModel, NetworkDiscoveryModel
from rxconfig import config

from bacnet_scan_api.models import ScanResponse, ObjectListNamesResponse

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
BACNET_SCAN_TOOL_PREFIX = f"{TOOLS_PREFIX}/bacnet_scan_api"
DEFAULT_TIMEOUT = 5.0  # 5 seconds timeout

# Global client
_client: Optional[httpx.AsyncClient] = None

def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        # Create a new client with reasonable defaults
        # We set a minimal keep-alive timeout to avoid stale connections
        _client = httpx.AsyncClient(
            follow_redirects=True, 
            timeout=DEFAULT_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    return _client

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
    client = get_client()
    try:
        response = await client.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response
    except httpx.TimeoutException:
        raise ApiError(408, f"Request timed out connecting to {url}")
    except httpx.HTTPStatusError as e:
        raise ApiError(e.response.status_code, e.response.text)
    except Exception as e:
        raise ApiError(500, str(e))

async def post_request(url: str, data: Optional[dict[str, Any]] = None, timeout: float = DEFAULT_TIMEOUT, params: Optional[dict[str, Any]] = None) -> httpx.Response:
    """Send an async POST request to the specified URL with optional JSON data and query params."""
    client = get_client()
    try:
        response = await client.post(url, json=data, params=params, timeout=timeout)
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
    client = get_client()
    try:
        response = await client.put(url, json=data, timeout=timeout)
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
    client = get_client()
    try:
        response = await client.delete(url, params=params, timeout=timeout)
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
    client = get_client()
    try:
        response = await client.request(
            method=request_type,
            url=url, 
            timeout=timeout, 
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

# TODO remove this function as it is a duplicate of proxy_request. this was required to make certain endpoint work when we didnt have some code
# available
async def request(url: str, method: Literal["POST", "GET", "PUT"] ="", timeout: float = DEFAULT_TIMEOUT, **kwargs) -> httpx.Response:
    """Send an async POST request to the specified URL with optional JSON data."""
    client = get_client()
    try:
        response = await client.request(
            method=method,
            url=url, 
            timeout=timeout, 
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
    """Get platform status - uses longer timeout for SSH/Ansible operations"""
    return await get_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/status/{platform_id}", timeout=60.0)

async def check_platform_connection(platform_id: str) -> dict:
    """Check the connection status of a platform - uses longer timeout for SSH"""
    response = await get_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/connection/{platform_id}", timeout=30.0)
    return response.json() if hasattr(response, 'json') else response

async def mark_platform_deployed(platform_id: str, deployed: bool = True) -> dict:
    """Mark a platform as deployed (or not deployed) without running deployment."""
    response = await post_request(
        f"{API_BASE_URL}{PLATFORMS_PREFIX}/mark-deployed/{platform_id}",
        params={"deployed": deployed},
        timeout=30.0
    )
    return response.json() if hasattr(response, 'json') else response

@with_model(ReachableResponse)
async def ping_resolvable_host(host_id: str) -> ReachableResponse:
    """Ping a host to check if it is reachable - uses longer timeout for SSH"""
    return await get_request(f"{API_BASE_URL}{TASK_PREFIX}/ping/{host_id}", timeout=30.0)

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
async def get_bacnet_host_ip() -> WindowsHostIPModel:
    """Get Windows host IP address for WSL2 users."""
    return await proxy_request(f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/get_host_ip", "GET")

@with_model(NetworkDiscoveryModel)
async def discover_networks(verbose: bool = False) -> NetworkDiscoveryModel:
    """Discover available networks for BACnet scanning using comprehensive network analysis."""
    params = {"verbose": verbose}
    return await proxy_request(f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/discover_networks", "GET", params=params)

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

@with_model(ScanResponse)
async def scan_bacnet_subnet(network_str: str) -> ScanResponse:
    """Scan a BACnet IP range for devices."""
    return await proxy_request(
        f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/bacnet/scan_subnet",
        "POST",
        timeout=600.0,
        params={"network_str": network_str}
    )

@with_model(ObjectListNamesResponse)
async def read_bacnet_object_list_names(request: BACnetReadObjectListRequest) -> ObjectListNamesResponse:
    """Read object list names from a BACnet device."""
    return await proxy_request(
        f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/bacnet/read_object_list_names",
        "POST",
        timeout=60.0,
        params=request.model_dump()
    )

async def read_bacnet_property(request: BACnetReadPropertyRequest, TIMEOUT: float=60.0):
    """Read a property from a BACnet device."""
    response = await proxy_request(
        f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/read_property",
        "POST",
        timeout=TIMEOUT,
        json=request.model_dump()
    )
    return response.json()

async def write_bacnet_property(request: BACnetWritePropertyRequest):
    """Write a property to a BACnet device."""
    from loguru import logger
    logger.debug(f"we got hit with: {request.model_dump()}")
    response = await proxy_request(
        f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/write_property",
        "POST",
        json=request.model_dump()
    )
    return response.json()

async def read_bacnet_device_all(request: BACnetReadDeviceAllRequest, timeout: float = 600.0) -> dict:
    """Read all properties from a BACnet device."""
    try:
        from loguru import logger
        logger.debug(f'thin endpoint wrapper says: {request.model_dump()}')
        response = await proxy_request(
            f"{API_BASE_URL}{BACNET_SCAN_TOOL_PREFIX}/bacnet/read_device_all",
            "POST",
            timeout=timeout,
            json=request.model_dump()
        )
        return response.json()
    except ApiError as e:
        # Log error but provide a response that won't break client code
        logger.debug(f"Error in read_bacnet_device_all: {e}")
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

async def deploy_platform(platform_id: str, password: str):
    # Long timeout for git installs which may need to clone and compile
    return await request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/deploy/{platform_id}", "POST", timeout=600.0, params={"password":password})

async def get_deploy_progress(platform_id: str):
    """Fetch deployment progress for a platform."""
    response = await get_request(
        f"{API_BASE_URL}{PLATFORMS_PREFIX}/deploy_progress/{platform_id}",
        timeout=5.0
    )
    return response.json()

async def install_python310(platform_id: str):
    """Install Python 3.10 via pyenv on the remote host and create the venv."""
    return await post_request(
        f"{API_BASE_URL}{PLATFORMS_PREFIX}/install_python310/{platform_id}",
        timeout=900.0
    )

async def add_host(host: CreateOrUpdateHostEntryRequest):
    await post_request(f"{API_BASE_URL}{HOSTS_PREFIX}", data=host.model_dump())

async def start_platform(platform_id: str):
    """Start a VOLTTRON platform"""
    # Longer timeout: backend waits up to 90s for VOLTTRON to start, plus SSH overhead
    return await post_request(
        f"{API_BASE_URL}{ANSIBLE_PREFIX}/start_platform/{platform_id}",
        timeout=180.0
    )

async def stop_platform(platform_id: str):
    """Stop a VOLTTRON platform"""
    return await post_request(
        f"{API_BASE_URL}{ANSIBLE_PREFIX}/stop_platform/{platform_id}",
        timeout=60.0
    )


async def detect_existing_volttron(ssh_host: str, ssh_user: str, ssh_port: str = "22") -> dict:
    """Detect an existing VOLTTRON installation on a remote machine"""
    response = await post_request(
        f"{API_BASE_URL}{ANSIBLE_PREFIX}/detect_existing_volttron",
        params={"ssh_host": ssh_host, "ssh_user": ssh_user, "ssh_port": ssh_port},
        timeout=30.0
    )
    return response.json()


async def get_platform_logs(platform_id: str, lines: int = 100):
    """Fetch VOLTTRON log contents from remote platform"""
    response = await get_request(
        f"{API_BASE_URL}{ANSIBLE_PREFIX}/platform/{platform_id}/logs",
        params={"lines": lines},
        timeout=10.0
    )
    return response.json()

async def delete_platform_logs(platform_id: str):
    """Delete VOLTTRON log file from remote platform"""
    response = await delete_request(
        f"{API_BASE_URL}{ANSIBLE_PREFIX}/platform/{platform_id}/logs",
        timeout=10.0
    )
    return response.json()

async def start_agent(platform_id: str, agent_id: str):
    """Start a specific agent on a VOLTTRON platform"""
    return await post_request(
        f"{API_BASE_URL}{ANSIBLE_PREFIX}/start_agent/{platform_id}/{agent_id}",
        timeout=30.0
    )

async def stop_agent(platform_id: str, agent_id: str):
    """Stop a specific agent on a VOLTTRON platform"""
    return await post_request(
        f"{API_BASE_URL}{ANSIBLE_PREFIX}/stop_agent/{platform_id}/{agent_id}",
        timeout=30.0
    )


async def install_agent(
    platform_id: str,
    agent_identity: str,
    agent_source: str,
    start_agent: bool = True,
    agent_config: str = None
):
    """Install an agent on a running VOLTTRON platform.

    Args:
        platform_id: The platform instance name
        agent_identity: The VIP identity for the agent
        agent_source: The pip package name (e.g., 'volttron-listener')
        start_agent: Whether to start the agent after installation
        agent_config: Optional path to agent config file on remote system
    """
    params = {
        "agent_identity": agent_identity,
        "agent_source": agent_source,
        "start_agent": start_agent,
    }
    if agent_config:
        params["agent_config"] = agent_config

    return await post_request(
        f"{API_BASE_URL}{ANSIBLE_PREFIX}/install_agent/{platform_id}",
        params=params,
        timeout=120.0  # Agent installation can take a while
    )


async def remove_agent(platform_id: str, agent_uuid: str):
    """Remove/uninstall an agent from a running VOLTTRON platform.

    Args:
        platform_id: The platform instance name
        agent_uuid: The UUID of the agent to remove
    """
    return await post_request(
        f"{API_BASE_URL}{ANSIBLE_PREFIX}/remove_agent/{platform_id}/{agent_uuid}",
        timeout=30.0
    )


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

async def delete_remote_volttron_files(platform_id: str) -> dict:
    """Delete VOLTTRON files on the remote system (VOLTTRON_HOME and venv)."""
    response = await delete_request(f"{API_BASE_URL}{ANSIBLE_PREFIX}/delete_remote_files/{platform_id}", timeout=120.0)
    return response.json() if hasattr(response, 'json') else response

async def remove_from_inventory(host_id: str):
    await delete_request(f"{API_BASE_URL}{HOSTS_PREFIX}/{host_id}")

async def delete_agent(platform_id: str, agent_id: str):
    await delete_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}/agents/{agent_id}")

async def delete_tool_proxy(tool_name: str, path: str, **kwargs) -> httpx.Response:
    await delete_request(f"{API_BASE_URL}/{TOOL_PROXY_PREFIX}/{tool_name}/{path}", "DELETE", **kwargs)
