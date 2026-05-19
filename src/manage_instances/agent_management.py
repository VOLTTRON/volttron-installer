import asyncio
import json
import os
import shutil
import signal
import shlex
from pathlib import Path


COMMAND_TIMEOUT = 600


class PlatformCommandError(Exception):
    def __init__(self, message: str, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


def _expand(path: str | None) -> str:
    return os.path.expanduser(path or "")


def _vctl_path(venv_path: str) -> str:
    return os.path.join(_expand(venv_path), "bin", "vctl")


async def _run_in_platform_env(
    venv_path: str,
    volttron_home: str,
    command: str,
    timeout: int = COMMAND_TIMEOUT,
) -> tuple[str, str]:
    expanded_venv = _expand(venv_path)
    expanded_home = _expand(volttron_home)
    vctl_exec = _vctl_path(venv_path)

    if not os.path.exists(vctl_exec):
        raise PlatformCommandError(f"vctl executable not found at {vctl_exec}")

    shell_command = f"""
set -e
export VOLTTRON_HOME={shlex.quote(expanded_home)}
source {shlex.quote(os.path.join(expanded_venv, "bin", "activate"))}
{command}
"""

    process = await asyncio.create_subprocess_shell(
        shell_command,
        executable="/bin/bash",
        start_new_session=True,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            process.kill()
        await process.communicate()
        raise PlatformCommandError(f"Command timed out after {timeout} seconds") from exc

    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")
    if process.returncode != 0:
        detail = stderr.strip() or stdout.strip() or f"Command exited with {process.returncode}"
        raise PlatformCommandError(detail, stdout=stdout, stderr=stderr)
    return stdout, stderr


def _parse_status_json(stdout: str) -> list[dict]:
    json_start = stdout.find("{")
    if json_start == -1:
        return []

    try:
        payload = json.loads(stdout[json_start:])
    except json.JSONDecodeError:
        return []

    def normalize(identity: str, info: dict) -> dict:
        status = info.get("status", "") or ""
        return {
            "identity": identity,
            "uuid": info.get("agent_uuid") or info.get("uuid") or "",
            "name": info.get("name") or identity,
            "tag": info.get("agent_tag") or info.get("tag") or "",
            "priority": str(info.get("priority", "")),
            "status": status,
            "health": _health_text(info.get("health")),
            "state": "running" if status.lower().startswith("running") else "stopped",
        }

    agents: list[dict] = []
    if isinstance(payload, dict):
        for identity, info in payload.items():
            if isinstance(info, dict):
                agents.append(normalize(identity, info))
    elif isinstance(payload, list):
        for info in payload:
            if isinstance(info, dict):
                identity = info.get("identity") or info.get("agent_identity") or info.get("name")
                if identity:
                    agents.append(normalize(identity, info))
    return agents


def _health_text(value) -> str:
    if isinstance(value, dict):
        return value.get("message", "")
    return str(value) if value else ""


async def list_agents(instance: dict) -> list[dict]:
    try:
        stdout, _ = await _run_in_platform_env(
            instance.get("venv"),
            instance.get("volttron_home"),
            "vctl --json status",
            timeout=5,
        )
    except PlatformCommandError as exc:
        if "No installed Agents found" in exc.stderr or "No installed Agents found" in exc.stdout:
            return []
        raise
    return _parse_status_json(stdout)


async def install_agent(
    instance: dict,
    agent_source: str,
    agent_identity: str = "",
    start_agent: bool = True,
    agent_config: str = "",
) -> str:
    source = shlex.quote(agent_source.strip())
    command = f"vctl install {source}"
    if agent_identity.strip():
        command += f" --vip-identity {shlex.quote(agent_identity.strip())}"
    if agent_config.strip():
        command += f" --agent-config {shlex.quote(agent_config.strip())}"
    if start_agent:
        command += " --start"

    stdout, stderr = await _run_in_platform_env(
        instance.get("venv"),
        instance.get("volttron_home"),
        command,
    )
    return stdout or stderr


async def list_libraries(instance: dict) -> list[dict]:
    venv_path = _expand(instance.get("venv"))
    python_exec = os.path.join(venv_path, "bin", "python")
    if not os.path.exists(python_exec):
        raise PlatformCommandError(f"Python executable not found at {python_exec}")

    process = await asyncio.create_subprocess_exec(
        python_exec,
        "-m",
        "pip",
        "list",
        "--format=json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")
    if process.returncode != 0:
        detail = stderr.strip() or stdout.strip() or f"pip list exited with {process.returncode}"
        raise PlatformCommandError(detail, stdout=stdout, stderr=stderr)

    try:
        packages = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise PlatformCommandError("Could not parse pip list output", stdout=stdout, stderr=stderr) from exc

    libraries = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        name = str(package.get("name", ""))
        normalized_name = name.lower().replace("_", "-")
        if "volttron-lib" in normalized_name:
            libraries.append({
                "name": name,
                "version": str(package.get("version", "")),
            })
    return sorted(libraries, key=lambda item: item["name"].lower())


async def install_library(
    instance: dict,
    library_source: str,
    force: bool = False,
    allow_prerelease: bool = False,
) -> str:
    clean_source = library_source.strip()
    if not clean_source:
        raise PlatformCommandError("Library source is required.")

    command = "vctl install-lib"
    if force:
        command += " --force"
    if allow_prerelease:
        command += " --pre-release"
    command += f" {shlex.quote(clean_source)}"

    stdout, stderr = await _run_in_platform_env(
        instance.get("venv"),
        instance.get("volttron_home"),
        command,
    )
    return stdout or stderr


async def remove_library(instance: dict, library_name: str) -> str:
    stdout, stderr = await _run_in_platform_env(
        instance.get("venv"),
        instance.get("volttron_home"),
        f"vctl remove-lib {shlex.quote(library_name)}",
        timeout=120,
    )
    return stdout or stderr


async def start_agent(instance: dict, agent_id: str) -> str:
    stdout, stderr = await _run_in_platform_env(
        instance.get("venv"),
        instance.get("volttron_home"),
        f"vctl start {shlex.quote(agent_id)}",
        timeout=60,
    )
    return stdout or stderr


async def stop_agent(instance: dict, agent_id: str) -> str:
    stdout, stderr = await _run_in_platform_env(
        instance.get("venv"),
        instance.get("volttron_home"),
        f"vctl stop {shlex.quote(agent_id)}",
        timeout=60,
    )
    return stdout or stderr


async def remove_agent(instance: dict, agent_id: str) -> str:
    stdout, stderr = await _run_in_platform_env(
        instance.get("venv"),
        instance.get("volttron_home"),
        f"vctl remove {shlex.quote(agent_id)}",
        timeout=60,
    )
    return stdout or stderr


async def shutdown_platform(instance: dict) -> str:
    try:
        stdout, stderr = await _run_in_platform_env(
            instance.get("venv"),
            instance.get("volttron_home"),
            "vctl shutdown --platform",
            timeout=120,
        )
        return stdout or stderr
    except PlatformCommandError as exc:
        message = f"{exc}\n{exc.stderr}\n{exc.stdout}"
        if "shutdown_agents" not in message or "operation timed out" not in message:
            raise

        if not instance.get("is_local"):
            raise

        from src.manage_instances.status_check import is_local_volttron_process_running

        for _ in range(10):
            if not is_local_volttron_process_running(instance.get("volttron_home")):
                return "Platform stopped after an agent shutdown timeout warning."
            await asyncio.sleep(1)

        raise


def _safe_rmtree(path_value: str | None) -> str:
    path = Path(_expand(path_value)).resolve()
    home = Path.home().resolve()

    if not path_value:
        return "No path configured"
    if path in {Path("/"), home} or len(path.parts) < 3:
        raise PlatformCommandError(f"Refusing to delete unsafe path: {path}")
    if not path.exists():
        return f"Skipped missing path: {path}"

    shutil.rmtree(path)
    return f"Deleted {path}"


async def delete_platform_files(instance: dict) -> list[str]:
    """
    Shut down the platform if possible, then remove its venv and VOLTTRON_HOME.

    The instance record is intentionally deleted by db.delete_instance after this
    cleanup succeeds, so a failed filesystem cleanup does not orphan a UI record.
    """
    messages: list[str] = []

    try:
        await shutdown_platform(instance)
        messages.append("Platform shutdown command completed")
    except PlatformCommandError as exc:
        vctl_missing = "vctl executable not found" in str(exc)
        already_down = "Connection refused" in str(exc) or "No route to host" in str(exc)
        if vctl_missing or already_down:
            messages.append(f"Shutdown skipped: {exc}")
        else:
            messages.append(f"Shutdown warning: {exc}")

    for path_value in (instance.get("venv"), instance.get("volttron_home")):
        messages.append(_safe_rmtree(path_value))

    return messages


def read_log_tail(instance: dict, line_count: int = 200) -> str:
    log_path = Path(_expand(instance.get("volttron_home"))) / "volttron.log"
    if not log_path.exists():
        return f"Log file not found at {log_path}"

    try:
        with log_path.open("r", errors="replace") as file:
            lines = file.readlines()
    except OSError as exc:
        return f"Could not read log file: {exc}"
    return "".join(lines[-line_count:]) or "Log file is empty."


def clear_log(instance: dict) -> str:
    log_path = Path(_expand(instance.get("volttron_home"))) / "volttron.log"
    if not log_path.parent.exists():
        raise PlatformCommandError(f"VOLTTRON_HOME does not exist at {log_path.parent}")

    try:
        with log_path.open("w"):
            pass
    except OSError as exc:
        raise PlatformCommandError(f"Could not clear log file: {exc}") from exc
    return f"Cleared {log_path}"
