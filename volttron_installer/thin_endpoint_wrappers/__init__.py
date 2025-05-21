import httpx, asyncio
from typing import Any, Optional, TypeVar, Type, Union, List, Dict

from volttron_installer.backend.endpoints import ping_resolvable_host
from ..backend.models import AgentType, HostEntry, PlatformDefinition, \
    CreatePlatformRequest, CreateOrUpdateHostEntryRequest, ReachableResponse, \
    PlatformDeploymentStatus, CreateAgentRequest

API_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"
ANSIBLE_PREFIX = f"{API_PREFIX}/ansible"
PLATFORMS_PREFIX = f"{API_PREFIX}/platforms"
HOSTS_PREFIX = f"{ANSIBLE_PREFIX}/hosts"
CATALOG_PREFIX = f"{API_PREFIX}/catalog"
TASK_PREFIX = f"{API_PREFIX}/task"

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

async def post_request(url: str, data: Optional[dict[str, Any]] = None,
                       timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
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

# PUT requests
async def update_platform(platform_id: str, platform: CreatePlatformRequest):
    await put_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}", data=dict(id=platform_id, platform=platform))

async def update_agent(platform_id: str, agent_id: str, agent: CreateAgentRequest):
    await put_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}/agents/{agent_id}", data=dict(agent=agent))

# POST requests
async def create_platform(platform: CreatePlatformRequest):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/", data=dict(platform=platform))

async def deploy_platform(platform_id: str):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/deploy/{platform_id}")

async def add_host(host: CreateOrUpdateHostEntryRequest):
    await post_request(f"{API_BASE_URL}{HOSTS_PREFIX}/", data=dict(host_entry=host))

async def start_platform(platform_id: str):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/start_platform", data=dict(platform_id=platform_id))

async def stop_platform(platform_id: str):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/stop_platform", data=dict(platform_id=platform_id))

async def create_agent(platform_id: str, agent: CreateAgentRequest):
    await post_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}/agents", data=dict(agent=agent))

# DELETE requests
async def delete_platform(platform_id: str):
    await delete_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}")

async def remove_from_inventory(host_id: str):
    await delete_request(f"{API_BASE_URL}{HOSTS_PREFIX}/{host_id}")

async def delete_agent(platform_id: str, agent_id: str):
    await delete_request(f"{API_BASE_URL}{PLATFORMS_PREFIX}/{platform_id}/agents/{agent_id}")