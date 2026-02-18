"""Discovers local custom VOLTTRON agents from the user's workspace directory."""
import asyncio
from pathlib import Path
from loguru import logger
from ..models import AgentType

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]  # Python 3.10 fallback


async def scan_local_agents(workspace_dir: str) -> list[AgentType]:
    """
    Scan workspace_dir for local VOLTTRON agent directories.

    Each valid agent directory must contain a pyproject.toml.
    Returns a list of AgentType with is_local=True and local_path set.
    """
    workspace = Path(workspace_dir).expanduser().resolve()

    if not workspace.exists() or not workspace.is_dir():
        logger.warning(f"Local agents workspace does not exist: {workspace}")
        return []

    def _scan() -> list[AgentType]:
        found: list[AgentType] = []
        for entry in sorted(workspace.iterdir()):
            if not entry.is_dir():
                continue
            pyproject_path = entry / "pyproject.toml"
            if not pyproject_path.exists():
                continue
            try:
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                # Support both [tool.poetry] and [project] table styles
                poetry = data.get("tool", {}).get("poetry", {})
                project = data.get("project", {})

                name: str = poetry.get("name") or project.get("name") or entry.name
                description: str = poetry.get("description") or project.get("description") or ""
                version: str = str(poetry.get("version") or project.get("version") or "unknown")

                # Strip "volttron-" prefix for the VIP identity
                identity = name[len("volttron-"):] if name.startswith("volttron-") else name

                found.append(AgentType(
                    identity=identity,
                    default_config={"_description": description, "_version": version},
                    default_config_store={},
                    source=str(entry),   # absolute path — usable as pip source
                    is_local=True,
                    local_path=str(entry),
                    config_store_allowed=False,
                ))
            except Exception as exc:
                logger.warning(f"Skipping {entry.name}: failed to parse pyproject.toml — {exc}")
                continue
        return found

    return await asyncio.get_event_loop().run_in_executor(None, _scan)
