"""Private helper functions shared across endpoint modules."""

from fastapi import HTTPException
from typing import Optional
import os, shlex, re
import json
import urllib.request
from urllib.parse import urlparse, parse_qs
from loguru import logger

from volttron_installer.backend.services.ansible_service import AnsibleService, get_ansible_service
from volttron_installer.backend.services.inventory_service import InventoryService, get_inventory_service
from volttron_installer.backend.services.platform_service import PlatformService, get_platform_service

from ..models import (
    HostEntry,
    PlatformConfig,
    PlatformDefinition,
)

# Deployment progress tracking (in-memory)
DEPLOY_PROGRESS: dict[str, dict] = {}


def _init_deploy_progress(platform_id: str, total_steps: int | None = None) -> None:
    DEPLOY_PROGRESS[platform_id] = {
        "status": "running",
        "current_task": "Starting deployment...",
        "progress": 0,
        "steps": [],
        "logs": [],
        "total_steps": total_steps,
    }


def _append_deploy_log(platform_id: str, message: str) -> None:
    if platform_id not in DEPLOY_PROGRESS:
        _init_deploy_progress(platform_id)
    DEPLOY_PROGRESS[platform_id]["logs"].append(message)


def _set_deploy_step(platform_id: str, step_name: str, status: str, progress: int | None = None) -> None:
    if platform_id not in DEPLOY_PROGRESS:
        _init_deploy_progress(platform_id)
    steps = DEPLOY_PROGRESS[platform_id]["steps"]
    for step in steps:
        if step["name"] == step_name:
            step["status"] = status
            break
    else:
        steps.append({"name": step_name, "status": status})

    DEPLOY_PROGRESS[platform_id]["current_task"] = step_name
    if progress is not None:
        DEPLOY_PROGRESS[platform_id]["progress"] = progress


def _normalize_host_identity(host: HostEntry) -> str:
    if host.ansible_connection == "local":
        return "local"
    return (host.ansible_host or host.id or "").strip().lower()


def _sanitize_instance_suffix(instance_name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "-", (instance_name or "").strip())
    return sanitized.strip("-") or "instance"


def _normalize_path(path: str) -> str:
    return (path or "").strip().rstrip("/")


def _extract_vip_port(vip_address: str) -> int | None:
    match = re.match(r"^tcp://[^:]+:(\d+)$", vip_address or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _compute_effective_instance_paths(host: HostEntry, config: PlatformConfig) -> tuple[str, str]:
    suffix = _sanitize_instance_suffix(config.instance_name)
    venv_override = getattr(config, "volttron_venv_override", "") or ""
    home_override = getattr(config, "volttron_home_override", "") or ""

    if venv_override.strip():
        venv_path = venv_override.strip()
    else:
        base_venv = host.volttron_venv or "~/volttron.venv"
        if base_venv.strip() == "~/volttron.venv":
            venv_path = f"~/.volttron/venvs/{suffix}"
        else:
            venv_path = f"{base_venv}.{suffix}"

    if home_override.strip():
        volttron_home = home_override.strip()
    else:
        base_home = host.volttron_home or "~/.volttron"
        if base_home.strip() == "~/.volttron":
            volttron_home = f"~/.volttron/instances/{suffix}"
        else:
            volttron_home = f"{base_home}.{suffix}"

    return venv_path, volttron_home


async def _resolve_platform_host(
    inventory_service: InventoryService,
    platform: PlatformDefinition,
    lookup_key: str,
) -> HostEntry | None:
    all_hosts = await inventory_service.get_hosts()
    host = all_hosts.get(platform.config.instance_name)
    if host is not None:
        return host

    host = all_hosts.get(lookup_key)
    if host is not None:
        return host

    return await inventory_service.get_host(platform.host_id)


async def _validate_no_same_host_conflicts(
    candidate_platform: PlatformDefinition,
    candidate_host: HostEntry,
    inventory_service: InventoryService,
    platform_service: PlatformService,
    ignore_instance_name: str | None = None,
) -> None:
    all_platforms = await platform_service.get_all_platforms()
    all_hosts = await inventory_service.get_hosts()

    candidate_host_identity = _normalize_host_identity(candidate_host)
    candidate_venv, candidate_home = _compute_effective_instance_paths(candidate_host, candidate_platform.config)
    candidate_venv_norm = _normalize_path(candidate_venv)
    candidate_home_norm = _normalize_path(candidate_home)
    candidate_vip_port = _extract_vip_port(candidate_platform.config.vip_address)

    for existing_platform in all_platforms:
        existing_instance_name = existing_platform.config.instance_name
        if ignore_instance_name and existing_instance_name == ignore_instance_name:
            continue

        existing_host = all_hosts.get(existing_instance_name)
        if existing_host is None:
            existing_host = await inventory_service.get_host(existing_platform.host_id)
        if existing_host is None:
            continue

        if _normalize_host_identity(existing_host) != candidate_host_identity:
            continue

        existing_venv, existing_home = _compute_effective_instance_paths(existing_host, existing_platform.config)
        existing_venv_norm = _normalize_path(existing_venv)
        existing_home_norm = _normalize_path(existing_home)
        existing_vip_port = _extract_vip_port(existing_platform.config.vip_address)

        if existing_venv_norm == candidate_venv_norm:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Venv path collision on host '{candidate_host.ansible_host}': "
                    f"'{candidate_venv}' is already used by instance '{existing_instance_name}'."
                ),
            )

        if existing_home_norm == candidate_home_norm:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"VOLTTRON_HOME collision on host '{candidate_host.ansible_host}': "
                    f"'{candidate_home}' is already used by instance '{existing_instance_name}'."
                ),
            )

        if (
            candidate_vip_port is not None
            and existing_vip_port is not None
            and existing_vip_port == candidate_vip_port
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"VIP port collision on host '{candidate_host.ansible_host}': "
                    f"port {candidate_vip_port} is already used by instance '{existing_instance_name}'."
                ),
            )


async def _resolve_platform_host_and_paths(
    platform_id: str,
    inventory_service: InventoryService,
    platform_service: PlatformService,
) -> tuple[PlatformDefinition, HostEntry, str, str]:
    platform = await platform_service.get_platform(platform_id)
    if platform is None:
        raise HTTPException(status_code=404, detail=f"Platform {platform_id} not found")

    host = await _resolve_platform_host(inventory_service, platform, platform_id)
    if host is None:
        raise HTTPException(
            status_code=404,
            detail=f"Host entry for {platform.config.instance_name} not found in inventory",
        )

    venv_path, volttron_home = _compute_effective_instance_paths(host, platform.config)
    return platform, host, venv_path, volttron_home


def _finalize_deploy_progress(platform_id: str, status: str) -> None:
    if platform_id not in DEPLOY_PROGRESS:
        _init_deploy_progress(platform_id)
    DEPLOY_PROGRESS[platform_id]["status"] = status
    if status == "success":
        DEPLOY_PROGRESS[platform_id]["progress"] = 100


def _extract_github_repo(source: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL-like install source."""
    value = source.strip()
    if value.startswith("git+"):
        value = value[len("git+"):]
    if value.startswith("github.com/"):
        value = "https://" + value
    if not (value.startswith("http://") or value.startswith("https://")):
        return None

    parsed = urlparse(value)
    if parsed.netloc.lower() != "github.com":
        return None

    path = parsed.path.lstrip("/")
    if "@" in path:
        path = path.split("@", 1)[0]
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return None
    owner = parts[0]
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        return None
    return owner, repo


def _extract_subdirectory_from_source(source: str) -> str:
    """Return pip VCS #subdirectory value when present, otherwise ''."""
    if "#" not in source:
        return ""
    fragment = source.split("#", 1)[1]
    query = parse_qs(fragment, keep_blank_values=True)
    subdirs = query.get("subdirectory", [])
    if not subdirs:
        return ""
    return subdirs[0].strip("/")


def _github_repo_has_python_project(owner: str, repo: str, subdirectory: str = "") -> tuple[bool, str]:
    """Check if a GitHub repo contains pyproject.toml or setup.py.

    Returns:
        (is_valid, reason)
    """
    api = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
    req = urllib.request.Request(api, headers={"Accept": "application/vnd.github+json", "User-Agent": "volttron-installer"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        # Don't hard-block installs on API/network failures; pip may still work.
        logger.warning(f"[INSTALL_DRIVER_LIB] GitHub preflight skipped for {owner}/{repo}: {exc}")
        return True, "preflight-skipped"

    tree = payload.get("tree", [])
    if not tree:
        return False, "Repository appears empty (no files found in main branch)."

    candidate_paths = {"pyproject.toml", "setup.py"}
    if subdirectory:
        candidate_paths = {f"{subdirectory}/{p}" for p in candidate_paths}

    seen_paths = {item.get("path", "") for item in tree}
    if any(path in seen_paths for path in candidate_paths):
        return True, "ok"

    if subdirectory:
        return False, (
            f"No pyproject.toml or setup.py found in subdirectory '{subdirectory}'. "
            "Use a correct #subdirectory value or a repo root that contains a Python package."
        )

    return False, (
        "No pyproject.toml or setup.py found at repository root. "
        "This repo does not appear to be an installable Python project."
    )


async def _validate_python_modules(ansible: AnsibleService, host: HostEntry, python_cmd: str) -> bool:
    """Check that a Python has required C extension modules for VOLTTRON.

    pyenv-built Pythons may lack _ctypes (needs libffi-dev) and _sqlite3 (needs libsqlite3-dev).
    These are required by pyzmq and VOLTTRON core respectively.
    """
    ret, _, _ = await ansible.run_ssh_command(
        host, f"{python_cmd} -c 'import _ctypes; import _sqlite3' 2>&1", timeout=10
    )
    return ret == 0


async def _select_python_cmd_for_host(host: HostEntry, ansible: AnsibleService, custom_python_path: str = "") -> str:
    """Select a supported Python command on the remote host (requires 3.10).

    Validates that the selected Python has the _ctypes module, which is required
    by pyzmq (a VOLTTRON dependency). pyenv-built Pythons may lack _ctypes if
    libffi-dev wasn't installed at build time.

    Args:
        host: Remote host entry
        ansible: Ansible service for running SSH commands
        custom_python_path: Optional custom Python path (e.g., ~/.pyenv/versions/3.10.14/bin/python3)

    Returns:
        Python command to use for deployment
    """
    # Candidate Python paths to try in order
    candidates = []

    # If custom Python path is provided, add it first
    if custom_python_path:
        candidates.append(custom_python_path.replace("~", "$HOME"))

    # Auto-detect candidates
    candidates.extend([
        "python3",
        "python3.10",
        "$HOME/.pyenv/versions/3.10.16/bin/python3",
        "$HOME/.pyenv/versions/3.10.14/bin/python3",
    ])

    # For local connections, also try the pixi environment Python (which is known to have _ctypes)
    is_local = hasattr(host, 'ansible_connection') and host.ansible_connection == 'local'
    if is_local:
        pixi_python = os.path.join(os.getcwd(), ".pixi/envs/default/bin/python3")
        candidates.insert(1 if not custom_python_path else 0, pixi_python)

    errors = []
    for python_cmd in candidates:
        # Check if the Python exists and get its version
        ret, stdout, stderr = await ansible.run_ssh_command(host, f"{python_cmd} -V 2>&1", timeout=10)
        if ret != 0:
            continue

        version_output = (stdout or stderr).strip()
        match = re.search(r"Python\s+(\d+)\.(\d+)", version_output)
        if not match:
            continue

        major, minor = int(match.group(1)), int(match.group(2))
        if major != 3 or minor != 10:
            errors.append(f"{python_cmd}: {version_output} (need 3.10)")
            continue

        # Validate that required C modules are available
        if await _validate_python_modules(ansible, host, python_cmd):
            logger.info(f"[PYTHON] Selected {python_cmd} ({version_output}) with all required modules")
            return python_cmd

        errors.append(f"{python_cmd}: {version_output} but missing required C modules (_ctypes/_sqlite3)")

    # If we get here, no suitable Python was found
    if errors:
        detail = "No suitable Python 3.10 found. Candidates tried:\n" + "\n".join(f"  - {e}" for e in errors)
    else:
        detail = "No Python 3.10 found on this host."

    suggestion = (
        "\n\nInstall a working Python 3.10 with required C modules:\n"
        "1. Install build deps: sudo apt-get install -y libffi-dev libsqlite3-dev\n"
        "2. Rebuild pyenv: pyenv install 3.10.16 --force\n"
        "3. Or set a custom Python path in Advanced Settings"
    )
    raise HTTPException(status_code=500, detail=detail + suggestion)


async def _deploy_modular_via_ssh(
    host: HostEntry,
    config: PlatformConfig,
    ansible: AnsibleService,
    python_cmd: str = "python3",
    venv_path: str = "~/volttron.venv",
    volttron_home: str = "~/.volttron",
    platform_id: str | None = None,
    agents: dict = None  # dict[str, AgentDefinition]
) -> dict:
    """
    Deploy modular VOLTTRON using direct SSH commands instead of Ansible playbooks.
    This is simpler, faster, and gives us more control over versions.

    Supports:
    - PyPI versions: "2.0.0rc20"
    - Git URLs: "git+https://github.com/username/volttron-core@branch"
    - Empty string: latest from PyPI

    TODO: Consider moving this to Ansible playbook later if needed for more complex deployments.
    """
    # Determine volttron-core package specification
    # Supports: empty (latest), version number, or git URL
    if config.volttron_version:
        if config.volttron_version.startswith("git+"):
            # Git URL provided directly (e.g., git+https://github.com/user/volttron-core@develop)
            core_pkg = config.volttron_version
        elif "/" in config.volttron_version or "@" in config.volttron_version:
            # Shorthand git URL (e.g., eclipse-volttron/volttron-core@develop)
            core_pkg = f"git+https://github.com/{config.volttron_version}"
        else:
            # Version number provided (e.g., 2.0.0rc20)
            core_pkg = f"volttron-core=={config.volttron_version}"
    else:
        # Default to latest from PyPI
        core_pkg = "volttron-core"

    steps = []

    total_steps = 7
    if platform_id:
        _init_deploy_progress(platform_id, total_steps=total_steps)

    # Step 1: Kill any existing VOLTTRON processes
    cmd = f'''VENV_PATH="{venv_path}"
VOLTTRON_HOME="{volttron_home}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
VOLTTRON_HOME="${{VOLTTRON_HOME/#\~/$HOME}}"
source "$VENV_PATH/bin/activate" 2>/dev/null || true
export VOLTTRON_HOME
"$VENV_PATH/bin/vctl" shutdown --platform 2>/dev/null || pkill -f "volttron -vv --log $VOLTTRON_HOME/volttron.log" 2>/dev/null || true
'''
    logger.info(f"[DEPLOY] Step 1: Killing existing VOLTTRON processes")
    if platform_id:
        _set_deploy_step(platform_id, "Kill existing processes", "running", progress=5)
        _append_deploy_log(platform_id, "[Step 1] Killing existing VOLTTRON processes")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)
    steps.append({"step": "Kill existing processes", "success": True, "output": stdout, "error": stderr})
    if platform_id:
        _set_deploy_step(platform_id, "Kill existing processes", "success", progress=10)
    # Don't fail if no processes to kill

    # Step 2: Create virtual environment
    cmd = f'''VENV_PATH="{venv_path}"
VENV_PATH="${{VENV_PATH/#\~/$HOME}}"
mkdir -p "$(dirname "$VENV_PATH")"
{python_cmd} -m venv "$VENV_PATH"'''
    logger.info(f"[DEPLOY] Step 2: Creating venv - {cmd}")
    if platform_id:
        _set_deploy_step(platform_id, "Create venv", "running", progress=20)
        _append_deploy_log(platform_id, f"[Step 2] Creating venv with {python_cmd}")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=60)
    steps.append({"step": "Create venv", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Create venv", "failed", progress=20)
        raise HTTPException(status_code=500, detail=f"Failed to create venv: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Create venv", "success", progress=25)

    # Step 3: Upgrade pip
    cmd = f"source {venv_path}/bin/activate && pip install --upgrade pip"
    logger.info(f"[DEPLOY] Step 3: Upgrading pip - {cmd}")
    if platform_id:
        _set_deploy_step(platform_id, "Upgrade pip", "running", progress=35)
        _append_deploy_log(platform_id, "[Step 3] Upgrading pip")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=120)
    steps.append({"step": "Upgrade pip", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Upgrade pip", "failed", progress=35)
        raise HTTPException(status_code=500, detail=f"Failed to upgrade pip: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Upgrade pip", "success", progress=40)

    # Step 4: Install VOLTTRON libraries first (these pull in dependencies like pyzmq)
    # This may install volttron-core from PyPI as a dependency
    cmd = f"source {venv_path}/bin/activate && pip install volttron-lib-zmq volttron-lib-auth"
    logger.info(f"[DEPLOY] Step 4: Installing VOLTTRON libraries")
    if platform_id:
        _set_deploy_step(platform_id, "Install VOLTTRON libs", "running", progress=55)
        _append_deploy_log(platform_id, "[Step 4] Installing VOLTTRON libs")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=300)
    steps.append({"step": "Install VOLTTRON libs", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Install VOLTTRON libs", "failed", progress=55)
        raise HTTPException(status_code=500, detail=f"Failed to install VOLTTRON libs: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Install VOLTTRON libs", "success", progress=60)

    # Step 5: Force reinstall volttron-core from the specified source
    # This overwrites any PyPI version that was pulled in by the libs
    cmd = f"source {venv_path}/bin/activate && pip install --no-cache-dir --force-reinstall {core_pkg}"
    logger.info(f"[DEPLOY] Step 5: Installing volttron-core - {core_pkg}")
    if platform_id:
        _set_deploy_step(platform_id, f"Install volttron-core ({core_pkg})", "running", progress=75)
        _append_deploy_log(platform_id, f"[Step 5] Installing volttron-core ({core_pkg})")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=300)
    steps.append({"step": f"Install volttron-core ({core_pkg})", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, f"Install volttron-core ({core_pkg})", "failed", progress=75)
        raise HTTPException(status_code=500, detail=f"Failed to install volttron-core: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, f"Install volttron-core ({core_pkg})", "success", progress=80)

    # Step 6: Create VOLTTRON_HOME directory
    cmd = f"mkdir -p {volttron_home}"
    logger.info(f"[DEPLOY] Step 6: Creating VOLTTRON_HOME - {cmd}")
    if platform_id:
        _set_deploy_step(platform_id, "Create VOLTTRON_HOME", "running", progress=90)
        _append_deploy_log(platform_id, "[Step 6] Creating VOLTTRON_HOME")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)
    steps.append({"step": "Create VOLTTRON_HOME", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Create VOLTTRON_HOME", "failed", progress=90)
        raise HTTPException(status_code=500, detail=f"Failed to create VOLTTRON_HOME: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Create VOLTTRON_HOME", "success", progress=92)

    # Step 7: Write config file
    # Note: Only write keys that modular VOLTTRON recognizes.
    # instance-name, messagebus, vip_address, volttron_type are installer-only fields
    # that cause VOLTTRON to crash on startup.
    config_content = f"""[volttron]
auth-enabled = True
server-messagebus-id = vip.server
agent-monitor-frequency = 600
enable-federation = False
enable-federation-cache = True
"""
    # Escape for shell
    config_escaped = config_content.replace("'", "'\\''")
    cmd = f"echo '{config_escaped}' > {volttron_home}/config"
    logger.info(f"[DEPLOY] Step 7: Writing config file")
    if platform_id:
        _set_deploy_step(platform_id, "Write config", "running", progress=96)
        _append_deploy_log(platform_id, "[Step 7] Writing config file")
    ret, stdout, stderr = await ansible.run_ssh_command(host, cmd, timeout=30)
    steps.append({"step": "Write config", "success": ret == 0, "output": stdout, "error": stderr})
    if ret != 0:
        if platform_id:
            _set_deploy_step(platform_id, "Write config", "failed", progress=96)
        raise HTTPException(status_code=500, detail=f"Failed to write config: {stderr or stdout}")
    if platform_id:
        _set_deploy_step(platform_id, "Write config", "success", progress=98)

    # -- Agent installation ---------------------------------------------------
    # Start the platform, install each pre-configured agent, then shut down.
    installable_agents = {k: v for k, v in (agents or {}).items() if v.source}
    if installable_agents:
        logger.info(f"[DEPLOY] Installing {len(installable_agents)} pre-deployment agents")

        # Start VOLTTRON in the background using nohup so it survives the SSH session ending.
        # Then poll vctl status until the platform reports running (up to 30s).
        venv_bin = venv_path.replace("~", "$HOME")
        vhome = volttron_home.replace("~", "$HOME")
        start_cmd = f'''VENV_BIN="{venv_bin}"
VHOME="{vhome}"
export VOLTTRON_HOME="$VHOME"
export PATH="$VENV_BIN/bin:$PATH"
. "$VENV_BIN/bin/activate"
nohup env VOLTTRON_HOME="$VHOME" PATH="$VENV_BIN/bin:$PATH" volttron -vv -l "$VHOME/volttron.log" </dev/null &>/dev/null &
disown
# Poll until platform is running (max 30 seconds)
for i in $(seq 1 30); do
  sleep 1
  if "$VENV_BIN/bin/vctl" status >/dev/null 2>&1; then
    echo "VOLTTRON_READY"
    break
  fi
done
'''
        if platform_id:
            _set_deploy_step(platform_id, "Start VOLTTRON for agent install", "running", progress=98)
            _append_deploy_log(platform_id, "[Agent install] Starting VOLTTRON platform")
        ret, stdout, stderr = await ansible.run_ssh_command(host, start_cmd, timeout=60)

        platform_started = "VOLTTRON_READY" in stdout
        steps.append({"step": "Start VOLTTRON for agent install", "success": platform_started, "output": stdout, "error": stderr})
        if platform_id:
            _set_deploy_step(platform_id, "Start VOLTTRON for agent install", "success" if platform_started else "failed", progress=98)

        if not platform_started:
            logger.warning(f"[DEPLOY] VOLTTRON did not start for agent installation")
        else:
            for agent_id, agent in installable_agents.items():
                source = shlex.quote(agent.source)
                identity = shlex.quote(agent.identity or agent_id)
                step_label = f"Install agent {agent.identity or agent_id}"
                logger.info(f"[DEPLOY] Installing agent {identity} from {source}")
                if platform_id:
                    _set_deploy_step(platform_id, step_label, "running", progress=99)
                    _append_deploy_log(platform_id, f"[Agent install] Installing {agent.identity or agent_id}")
                install_cmd = f'''VENV_BIN="{venv_bin}"
VHOME="{vhome}"
export VOLTTRON_HOME="$VHOME"
. "$VENV_BIN/bin/activate"
pip install --quiet {source}
"$VENV_BIN/bin/vctl" install {source} --vip-identity {identity} --start
'''
                ret, stdout, stderr = await ansible.run_ssh_command(host, install_cmd, timeout=300)
                steps.append({"step": step_label, "success": ret == 0, "output": stdout, "error": stderr})
                if ret != 0:
                    logger.warning(f"[DEPLOY] Failed to install agent {agent.identity}: {stderr or stdout}")
                    if platform_id:
                        _append_deploy_log(platform_id, f"[Agent install] WARNING: failed to install {agent.identity or agent_id}: {(stderr or stdout)[:200]}")
                        _set_deploy_step(platform_id, step_label, "failed", progress=99)
                else:
                    if platform_id:
                        _set_deploy_step(platform_id, step_label, "success", progress=99)

        # Shut VOLTTRON back down so user controls when it runs
        stop_cmd = f'''VENV_BIN="{venv_bin}"
VHOME="{vhome}"
export VOLTTRON_HOME="$VHOME"
. "$VENV_BIN/bin/activate"
"$VENV_BIN/bin/vctl" shutdown --platform 2>/dev/null || pkill -f "volttron -vv -l $VHOME/volttron.log" 2>/dev/null || true
sleep 3
'''
        if platform_id:
            _append_deploy_log(platform_id, "[Agent install] Shutting down VOLTTRON")
        await ansible.run_ssh_command(host, stop_cmd, timeout=30)
    # -- End agent installation -----------------------------------------------

    logger.info(f"[DEPLOY] Modular VOLTTRON deployed successfully")
    if platform_id:
        _finalize_deploy_progress(platform_id, "success")
    return {
        "status": "success",
        "message": "Modular VOLTTRON deployed via SSH",
        "steps": steps
    }


def _parse_ansible_tasks(ansible_output: str) -> list[str]:
    """Parse Ansible output to extract task names"""
    tasks = []
    for line in ansible_output.split('\n'):
        if line.startswith('TASK ['):
            # Extract task name from "TASK [task name] ***"
            task_name = line[6:line.rfind(']')].strip()
            tasks.append(task_name)
    return tasks


def _parse_ansible_error(return_code: int, stdout: str, stderr: str) -> str:
    """Parse Ansible output to provide a user-friendly error message.

    Analyzes both stdout and stderr to identify common failure patterns
    and returns a clear, actionable error message.
    """
    import re

    # First, look for specific error messages in fatal/FAILED lines (most reliable)
    # These lines contain the actual error from Ansible
    for line in stdout.split('\n'):
        line_lower = line.lower()
        if 'fatal:' in line_lower or 'failed!' in line_lower:
            # Check for specific errors in the fatal line
            if "incorrect sudo password" in line_lower:
                return "Authentication failed: The sudo password is incorrect."
            if "authentication failure" in line_lower:
                return "Authentication failed: The password is incorrect."
            if "permission denied" in line_lower:
                return "Authentication failed: The password is incorrect or the user doesn't have access."
            if "host key verification failed" in line_lower:
                return "SSH host key verification failed. Try enabling 'Disable Host Key Checking' in the connection settings."
            if "sudo: a password is required" in line_lower or "missing sudo password" in line_lower:
                return "Sudo password required: The remote user needs sudo privileges. Ensure the password is correct."
            if "not in the sudoers file" in line_lower:
                return "Permission denied: The remote user is not in the sudoers file and cannot run privileged commands."
            if "connection refused" in line_lower:
                return "Connection refused: The SSH service may not be running on the remote host, or the port may be blocked."
            if "timed out" in line_lower:
                return "Connection timed out: The host is not responding. Check network connectivity and firewall settings."
            if "name or service not known" in line_lower or "could not resolve" in line_lower:
                return "DNS resolution failed: The hostname could not be resolved. Check the hostname or use an IP address instead."
            if "command not found" in line_lower:
                return "Missing dependency: A required command was not found on the remote host."
            if "no python interpreter found" in line_lower:
                return "Python not found: No Python interpreter found on the remote host. Ensure Python is installed."
            # Check for UNREACHABLE in the fatal line itself (not in PLAY RECAP)
            if "unreachable!" in line_lower:
                return "Host unreachable: Unable to connect to the remote host. Check that the host is online and the IP/hostname is correct."

            # Extract the error message from the JSON-like output if present
            msg_match = re.search(r'"msg":\s*"([^"]+)"', line)
            if msg_match:
                return f"Deployment failed: {msg_match.group(1)}"

            # Return a truncated version of the fatal line
            return f"Deployment failed: {line.strip()[:300]}"

    # Check PLAY RECAP for unreachable hosts (unreachable > 0)
    for line in stdout.split('\n'):
        if 'unreachable=' in line.lower():
            match = re.search(r'unreachable=(\d+)', line.lower())
            if match and int(match.group(1)) > 0:
                return "Host unreachable: Unable to connect to the remote host. Check that the host is online and the IP/hostname is correct."

    # Filter out warnings from stderr to find real errors
    real_errors = []
    for line in stderr.split('\n'):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith('[WARNING]'):
            real_errors.append(line_stripped)

    # If we found real errors in stderr, use those
    if real_errors:
        return f"Deployment failed: {' '.join(real_errors[:3])}"

    # Generic fallback - include both outputs for debugging
    error_detail = stderr.strip() if stderr.strip() else stdout.strip()
    if len(error_detail) > 500:
        error_detail = error_detail[:500] + "..."
    return f"Deployment failed (exit code {return_code}): {error_detail}"