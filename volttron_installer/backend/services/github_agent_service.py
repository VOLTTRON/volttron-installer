"""Fetches modular VOLTTRON agent listings from the eclipse-volttron GitHub organization."""
import time
import httpx
from loguru import logger
from ..models import AgentType

GITHUB_API_URL = "https://api.github.com/orgs/eclipse-volttron/repos"

# Repos that are infrastructure / libraries, not installable agents
_EXCLUDE_REPOS = {
    "volttron-core",
    "volttron-testing",
    "volttron-boptest-integration",
    "volttron-ansible",
    "volttron-installer",
}

# In-memory cache: {"agents": list[AgentType] | None, "fetched_at": float}
_CACHE: dict = {"agents": None, "fetched_at": 0.0}
_CACHE_TTL_SECONDS = 300.0  # 5 minutes


def _parse_next_link(link_header: str) -> str | None:
    """Parse GitHub Link header for rel="next" URL."""
    for part in link_header.split(","):
        if 'rel="next"' in part:
            url_part = part.split(";")[0].strip()
            return url_part.strip("<>")
    return None


async def fetch_github_agents() -> tuple[list[AgentType], bool]:
    """
    Fetch modular VOLTTRON agents from eclipse-volttron GitHub org.

    Returns:
        (agents, is_offline) — is_offline is True when GitHub is unreachable.
        Uses in-memory cache with a 5-minute TTL.
    """
    now = time.monotonic()
    if _CACHE["agents"] is not None and (now - _CACHE["fetched_at"]) < _CACHE_TTL_SECONDS:
        logger.debug("Returning cached GitHub agent list")
        return _CACHE["agents"], False

    repos: list[dict] = []
    url: str | None = f"{GITHUB_API_URL}?per_page=100&type=public"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            while url and len(repos) < 300:
                response = await client.get(
                    url,
                    headers={"Accept": "application/vnd.github+json"},
                )
                response.raise_for_status()
                repos.extend(response.json())
                url = _parse_next_link(response.headers.get("Link", ""))
    except Exception as exc:
        logger.warning(f"GitHub agent fetch failed (offline mode): {exc}")
        return [], True

    agents: list[AgentType] = []
    for repo in repos:
        name: str = repo.get("name", "")
        if not name.startswith("volttron-"):
            continue
        if name in _EXCLUDE_REPOS:
            continue
        if repo.get("archived", False):
            continue

        # Strip "volttron-" prefix for the VIP identity
        identity = name[len("volttron-"):]
        description = repo.get("description") or ""

        agents.append(AgentType(
            identity=identity,
            default_config={"_description": description},
            default_config_store={},
            source=name,  # pip package name (e.g. "volttron-listener")
            config_store_allowed=True,
        ))

    _CACHE["agents"] = agents
    _CACHE["fetched_at"] = now
    logger.info(f"Fetched {len(agents)} agents from eclipse-volttron GitHub org")
    return agents, False
