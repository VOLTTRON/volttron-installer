"""BACnet scan API router endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Any

from ...utils.get_api_url import get_api_url
from ..tool_proxy_factory import ToolProxyFactory

from ..models import (
    BACnetReadPropertyRequest,
    BACnetWritePropertyRequest,
    BACnetReadDeviceAllRequest,
)

from bacnet_scan_api.models import ScanResponse, ObjectListNamesResponse

TOOLS_PREFIX = "/tools"

bacnet_scan_api_router = APIRouter(prefix=f"{TOOLS_PREFIX}/bacnet_scan_api", tags=["bacnet scan tool"])


@bacnet_scan_api_router.get("/get_local_ip", response_model=dict[str, str])
async def bacnet_scan_get_local_ip(target_ip: str = None) -> dict[str, str]:
    # OPTIONAL
    from ..tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/get_local_ip")
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

@bacnet_scan_api_router.post("/start_proxy", response_model=dict[str, Any])
async def bacnet_scan_start_proxy(local_device_address: str | None = None) -> dict[str, Any]:
    from ..tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/start_proxy")
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

@bacnet_scan_api_router.get("/get_host_ip", response_model=dict)
async def bacnet_scan_get_host_ip() -> dict:
    # OPTIONAL, for WSL2 users
    from ..tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/get_host_ip")
    try:
        response = await ToolProxyFactory.request(
            url,
            "GET",
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.get("/discover_networks", response_model=dict)
async def bacnet_discover_networks(verbose: bool = False) -> dict:
    """Discover available networks for BACnet scanning using comprehensive network analysis."""
    from ..tool_proxy_factory import ApiError

    url = get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/discover_networks")
    try:
        response = await ToolProxyFactory.request(
            url,
            "GET",
            params={"verbose": verbose}
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/bacnet/scan_subnet", response_model=ScanResponse)
async def bacnet_scan_subnet(network_str: str | None = None) -> dict[str, str]:
    from ..tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/bacnet/scan_subnet")
    REQUEST={"subnet": network_str}
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST,
            timeout=600.0
        )
        data = response.json()
        return ScanResponse(
            **data
        )
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/read_property", response_model=dict)
async def bacnet_scan_read_property(request: BACnetReadPropertyRequest) -> dict:
    from ..tool_proxy_factory import ApiError
    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/read_property")
    REQUEST = {
            "device_address": request.device_address,
            "object_identifier": request.object_identifier,
            "property_identifier": request.property_identifier,
            # "property_array_index": request.property_array_index
        }
    if request.property_array_index is not None:
        REQUEST["property_array_index"] = request.property_array_index
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

@bacnet_scan_api_router.post("/write_property", response_model=dict)
async def bacnet_scan_write_property(request: BACnetWritePropertyRequest) -> dict:
    from ..tool_proxy_factory import ApiError
    from loguru import logger

    logger.debug(f"this is i, the endpiont getting: {request}")
    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/write_property")
    REQUEST = {
            "device_address": request.device_address,
            "object_identifier": request.object_identifier,
            "property_identifier": request.property_identifier,
            "value": request.value,
            "priority": request.priority,
            # "property_array_index": request.property_array_index
        }
    if request.property_array_index is not None:
        REQUEST["property_array_index"] = request.property_array_index
    logger.debug(f"this is i, the endpoint, passing in: {REQUEST}")
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            params=REQUEST
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/bacnet/read_device_all")
async def bacnet_scan_read_device_all(request: BACnetReadDeviceAllRequest):
    from ..tool_proxy_factory import ApiError
    from loguru import logger
    logger.debug(f"this is i, the endpiont getting: {request}")

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/bacnet/read_device_all")
    REQUEST={
        "device_address": request.device_address,
        "device_object_identifier": request.device_object_identifier
        }
    logger.debug(f"and this is my REQUEST: {REQUEST}")

    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST,
            timeout=600.0
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/bacnet/who_is")
async def bacnet_scan_who_is(
        device_instance_low: int,
        device_instance_high: int,
        dest: str
    ) -> dict[str, str]:
    from ..tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/bacnet/who_is")
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

@bacnet_scan_api_router.post("/stop_proxy", response_model=dict[str, Any])
async def bacnet_scan_stop_proxy() -> dict[str, Any]:
    from ..tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/stop_proxy")
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
        )
        data = response.json()
        return data
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@bacnet_scan_api_router.post("/bacnet/read_object_list_names", response_model=ObjectListNamesResponse)
async def bacnet_scan_read_object_list_names(
    device_address: str,
    device_object_identifier: str,
    page: int = 1,
    page_size: int = 100
) -> ObjectListNamesResponse:
    from ..tool_proxy_factory import ApiError

    url=get_api_url.get_api_url("/api/tool_proxy/bacnet_scan_api/bacnet/read_object_list_names")
    REQUEST = {
        "device_address": device_address,
        "device_object_identifier": device_object_identifier,
        "page": page,
        "page_size": page_size
    }
    try:
        response = await ToolProxyFactory.request(
            url,
            "POST",
            data=REQUEST
        )
        data = response.json()
        return ObjectListNamesResponse(**data)
    except ApiError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)