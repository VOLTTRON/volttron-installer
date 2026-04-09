"""Catalog router endpoints."""

from fastapi import APIRouter, HTTPException
from loguru import logger

from volttron_installer.backend.services.github_agent_service import fetch_github_agents
from volttron_installer.backend.services.local_agent_service import scan_local_agents
from volttron_installer.backend.models import AgentCatalog
from volttron_installer.settings import get_settings

from ..models import (
    AgentType,
    GitHubAgentsResponse,
)

catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])


@catalog_router.get("/agents", response_model=dict[str, AgentType])
async def get_agent_catalog() -> dict[str, AgentType]:
    """Retrieves the agent catalog -- modular VOLTTRON agents only (those with a pip package source)."""
    try:
        catalog = AgentCatalog()
        return catalog.modular_agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@catalog_router.get("/agents/github", response_model=GitHubAgentsResponse)
async def get_github_agents() -> GitHubAgentsResponse:
    """Fetch modular VOLTTRON agents from the eclipse-volttron GitHub org.
    Falls back to the built-in modular catalog when offline."""
    try:
        agents, is_offline = await fetch_github_agents()
        if is_offline:
            catalog = AgentCatalog()
            fallback = list(catalog.modular_agents.values())
            return GitHubAgentsResponse(agents=fallback, offline=True)
        return GitHubAgentsResponse(agents=agents, offline=False)
    except Exception as e:
        logger.error(f"GitHub agent fetch error: {e}")
        catalog = AgentCatalog()
        fallback = list(catalog.modular_agents.values())
        return GitHubAgentsResponse(agents=fallback, offline=True)


@catalog_router.get("/agents/local", response_model=list[AgentType])
async def get_local_agents() -> list[AgentType]:
    """Scan the local workspace directory for custom agent directories."""
    try:
        settings = get_settings()
        return await scan_local_agents(settings.local_agents_dir)
    except Exception as e:
        logger.warning(f"Local agent scan failed: {e}")
        return []


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