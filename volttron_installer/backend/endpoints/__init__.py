"""Endpoints package -- re-exports all routers for backward compatibility."""

from .platform_endpoints import platform_router
from .ansible_endpoints import ansible_router
from .task_endpoints import task_router, tool_management_router
from .catalog_endpoints import catalog_router
from .bacnet_proxy_endpoints import bacnet_scan_api_router

__all__ = [
    "platform_router",
    "ansible_router",
    "task_router",
    "catalog_router",
    "tool_management_router",
    "bacnet_scan_api_router",
]