import asyncio
import json
import os
import shutil
import signal
import shlex
from pathlib import Path
from urllib.parse import quote

import httpx

from src import ssh_remote


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


async def _remote_expanded_path(instance: dict, key: str) -> str:
    cache_key = f"_expanded_{key}"
    if not instance.get(cache_key):
        instance[cache_key] = await ssh_remote.expand_path(instance, instance.get(key))
    return instance[cache_key]


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


async def _run_instance_platform_env(
    instance: dict,
    command: str,
    timeout: int = COMMAND_TIMEOUT,
) -> tuple[str, str]:
    if ssh_remote.is_remote_instance(instance):
        expanded_venv = await _remote_expanded_path(instance, "venv")
        expanded_home = await _remote_expanded_path(instance, "volttron_home")
        vctl_exec = f"{expanded_venv}/bin/vctl"
        exists = await ssh_remote.path_exists(instance, vctl_exec)
        if not exists:
            raise PlatformCommandError(f"vctl executable not found at {vctl_exec}")
        shell_command = f"""
set -e
export VOLTTRON_HOME={shlex.quote(expanded_home)}
source {shlex.quote(f"{expanded_venv}/bin/activate")}
{command}
"""
        try:
            return await ssh_remote.run(instance, shell_command, timeout=timeout)
        except ssh_remote.SSHCommandError as exc:
            raise PlatformCommandError(str(exc), stdout=exc.stdout, stderr=exc.stderr) from exc

    return await _run_in_platform_env(
        instance.get("venv"),
        instance.get("volttron_home"),
        command,
        timeout=timeout,
    )


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


async def _web_access_token(instance: dict, client: httpx.AsyncClient) -> str:
    web_address = instance.get("web_bind_address", "")
    username = instance.get("web_admin_user", "")
    password = instance.get("web_admin_pass", "")
    if not web_address or not username or not password:
        raise PlatformCommandError("No web API address or credentials are configured for this instance.")

    response = await client.post(
        f"{web_address.rstrip('/')}/authenticate",
        json={"username": username, "password": password},
    )
    if response.status_code >= 400:
        raise PlatformCommandError(f"Web authentication failed: HTTP {response.status_code} {response.text}")

    token = response.json().get("access_token")
    if not token:
        raise PlatformCommandError("Authentication response did not include an access token.")
    return token


async def _call_vui_rpc(instance: dict, agent_identity: str, method_name: str, args: list | None = None):
    web_address = instance.get("web_bind_address", "")
    if not web_address:
        raise PlatformCommandError("No web API address is configured for this instance.")

    platform = quote(instance.get("name", ""), safe="")
    agent = quote(agent_identity, safe="")
    method = quote(method_name, safe="")
    url = f"{web_address.rstrip('/')}/vui/platforms/{platform}/agents/{agent}/rpc/{method}"
    timeout = httpx.Timeout(8.0, connect=2.0)
    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        token = await _web_access_token(instance, client)
        response = await client.post(
            url,
            headers={"Authorization": f"BEARER {token}"},
            json={"args": args or []},
        )
        if response.status_code >= 400:
            raise PlatformCommandError(f"VUI RPC {agent_identity}.{method_name} failed: HTTP {response.status_code} {response.text}")
        return response.json()


def _status_from_aip_status(value) -> tuple[str, str]:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return "unknown", str(value) if value else ""

    pid, status_code = value[0], value[1]
    if status_code is None:
        detail = f"running (pid {pid})" if pid else "running"
        return "running", detail
    if pid:
        return "stopped", f"stopped (pid {pid}, status {status_code})"
    return "stopped", f"stopped (status {status_code})"


def _normalize_rest_agents(agent_infos: list, status_infos: list) -> list[dict]:
    status_by_uuid = {}
    status_by_identity = {}
    for item in status_infos if isinstance(status_infos, list) else []:
        if not isinstance(item, (list, tuple)) or len(item) < 4:
            continue
        uuid, name, status_value, identity = item[:4]
        state, status_text = _status_from_aip_status(status_value)
        status_record = {
            "uuid": uuid or "",
            "name": name or identity or "",
            "identity": identity or name or uuid or "",
            "state": state,
            "status": status_text,
        }
        if uuid:
            status_by_uuid[uuid] = status_record
        if identity:
            status_by_identity[identity] = status_record

    agents: list[dict] = []
    seen = set()
    for info in agent_infos if isinstance(agent_infos, list) else []:
        if not isinstance(info, dict):
            continue
        uuid = info.get("uuid") or ""
        identity = info.get("identity") or info.get("name") or uuid
        status_record = status_by_uuid.get(uuid) or status_by_identity.get(identity) or {}
        agents.append({
            "identity": identity,
            "uuid": uuid,
            "name": info.get("name") or status_record.get("name") or identity,
            "tag": info.get("tag") or "",
            "priority": str(info.get("priority") or ""),
            "status": status_record.get("status") or "installed",
            "health": "",
            "state": status_record.get("state") or "stopped",
        })
        seen.add(uuid or identity)

    for status_record in status_by_uuid.values():
        key = status_record.get("uuid") or status_record.get("identity")
        if key in seen:
            continue
        agents.append({
            "identity": status_record.get("identity", "unknown"),
            "uuid": status_record.get("uuid", ""),
            "name": status_record.get("name") or status_record.get("identity", "unknown"),
            "tag": "",
            "priority": "",
            "status": status_record.get("status", ""),
            "health": "",
            "state": status_record.get("state", "unknown"),
        })
    return sorted(agents, key=lambda item: item.get("identity", "").lower())


async def _list_agents_rest(instance: dict) -> list[dict]:
    agent_infos = await _call_vui_rpc(instance, "platform.control", "list_agents")
    status_infos = await _call_vui_rpc(instance, "platform.control", "status_agents")
    return _normalize_rest_agents(agent_infos, status_infos)


async def list_agents(instance: dict) -> list[dict]:
    if instance.get("web_bind_address") and instance.get("web_admin_user") and instance.get("web_admin_pass"):
        try:
            return await _list_agents_rest(instance)
        except PlatformCommandError:
            if ssh_remote.is_remote_instance(instance):
                raise
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            if ssh_remote.is_remote_instance(instance):
                raise PlatformCommandError("Web API is not reachable for remote agent display.") from exc
    elif ssh_remote.is_remote_instance(instance):
        raise PlatformCommandError("Remote agent display requires the VOLTTRON web API.")

    try:
        stdout, _ = await _run_instance_platform_env(
            instance,
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

    stdout, stderr = await _run_instance_platform_env(
        instance,
        command,
    )
    return stdout or stderr


async def list_libraries(instance: dict) -> list[dict]:
    if ssh_remote.is_remote_instance(instance):
        expanded_venv = await _remote_expanded_path(instance, "venv")
        python_exec = f"{expanded_venv}/bin/python"
        if not await ssh_remote.path_exists(instance, python_exec):
            raise PlatformCommandError(f"Python executable not found at {python_exec}")
        try:
            stdout, stderr = await ssh_remote.run(
                instance,
                f"{shlex.quote(python_exec)} -m pip list --format=json",
                timeout=120,
            )
        except ssh_remote.SSHCommandError as exc:
            raise PlatformCommandError(str(exc), stdout=exc.stdout, stderr=exc.stderr) from exc
        return _parse_library_list(stdout, stderr)

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

    return _parse_library_list(stdout, stderr)


def _parse_library_list(stdout: str, stderr: str = "") -> list[dict]:
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

    stdout, stderr = await _run_instance_platform_env(
        instance,
        command,
    )
    return stdout or stderr


async def remove_library(instance: dict, library_name: str) -> str:
    stdout, stderr = await _run_instance_platform_env(
        instance,
        f"vctl remove-lib {shlex.quote(library_name)}",
        timeout=120,
    )
    return stdout or stderr


async def start_agent(instance: dict, agent_id: str) -> str:
    stdout, stderr = await _run_instance_platform_env(
        instance,
        f"vctl start {shlex.quote(agent_id)}",
        timeout=60,
    )
    return stdout or stderr


async def stop_agent(instance: dict, agent_id: str) -> str:
    stdout, stderr = await _run_instance_platform_env(
        instance,
        f"vctl stop {shlex.quote(agent_id)}",
        timeout=60,
    )
    return stdout or stderr


async def remove_agent(instance: dict, agent_id: str) -> str:
    stdout, stderr = await _run_instance_platform_env(
        instance,
        f"vctl remove {shlex.quote(agent_id)}",
        timeout=60,
    )
    return stdout or stderr


async def shutdown_platform(instance: dict, sudo_password: str = "") -> str:
    if instance.get("deployment_method") == "ansible":
        service = f"volttron-{instance.get('name')}"
        if ssh_remote.is_remote_instance(instance):
            stdout, stderr = await ssh_remote.run(
                instance,
                f"sudo -n systemctl stop {shlex.quote(service)}",
                timeout=120,
            )
            return stdout or stderr or f"Stopped {service}"

        if os.geteuid() == 0:
            cmd = ["systemctl", "stop", service]
        elif sudo_password:
            cmd = ["sudo", "-S", "-p", "", "systemctl", "stop", service]
        else:
            cmd = ["sudo", "-n", "systemctl", "stop", service]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if sudo_password and os.geteuid() != 0 else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdin = f"{sudo_password}\n".encode() if sudo_password and os.geteuid() != 0 else None
        stdout, stderr = await process.communicate(stdin)
        if process.returncode != 0:
            detail = stderr.decode(errors="replace").strip() or stdout.decode(errors="replace").strip()
            raise PlatformCommandError(f"Could not stop {service} with systemd: {detail}")
        return stdout.decode(errors="replace") or stderr.decode(errors="replace") or f"Stopped {service}"

    try:
        stdout, stderr = await _run_instance_platform_env(
            instance,
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
        if ssh_remote.is_remote_instance(instance):
            messages.append(await ssh_remote.safe_rmtree(instance, path_value))
        else:
            messages.append(_safe_rmtree(path_value))

    return messages


async def read_log_tail(instance: dict, line_count: int = 200) -> str:
    if ssh_remote.is_remote_instance(instance):
        expanded_home = await _remote_expanded_path(instance, "volttron_home")
        return await ssh_remote.tail_file(instance, f"{expanded_home}/volttron.log", line_count)

    log_path = Path(_expand(instance.get("volttron_home"))) / "volttron.log"
    if not log_path.exists():
        return f"Log file not found at {log_path}"

    try:
        with log_path.open("r", errors="replace") as file:
            lines = file.readlines()
    except OSError as exc:
        return f"Could not read log file: {exc}"
    return "".join(lines[-line_count:]) or "Log file is empty."


async def clear_log(instance: dict) -> str:
    if ssh_remote.is_remote_instance(instance):
        expanded_home = await _remote_expanded_path(instance, "volttron_home")
        return await ssh_remote.truncate_file(instance, f"{expanded_home}/volttron.log")

    log_path = Path(_expand(instance.get("volttron_home"))) / "volttron.log"
    if not log_path.parent.exists():
        raise PlatformCommandError(f"VOLTTRON_HOME does not exist at {log_path.parent}")

    try:
        with log_path.open("w"):
            pass
    except OSError as exc:
        raise PlatformCommandError(f"Could not clear log file: {exc}") from exc
    return f"Cleared {log_path}"
