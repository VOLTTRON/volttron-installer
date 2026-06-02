import asyncio
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import yaml


ANSIBLE_COLLECTION_URL = "git+https://github.com/eclipse-volttron/volttron-ansible.git,develop"
ANSIBLE_ROOT = Path("ansible_deployments")
AUTO_PYTHON_INTERPRETER = "auto"
BOOTSTRAPPED_PYTHON_PATH = "{{ ansible_env.HOME }}/.local/bin/volttron-python3.10"
SUPPORTED_LOCAL_PYTHON = (3, 10)


@dataclass
class AnsibleDeploymentResult:
    inventory_path: Path
    config_root: Path
    host_alias: str
    web_credentials: dict[str, str]


class AnsibleDeployError(Exception):
    pass


def _find_executable(name: str) -> str | None:
    executable = shutil.which(name)
    if executable:
        return executable

    # TODO: Move Ansible executable discovery into app startup/configuration so deployment code
    # can receive explicit tool paths instead of searching local virtualenv layouts.
    venv_candidate = Path(sys.executable).resolve().parent / name
    if venv_candidate.exists() and os.access(venv_candidate, os.X_OK):
        return str(venv_candidate)

    project_venv_candidate = Path.cwd() / ".venv" / "bin" / name
    if project_venv_candidate.exists() and os.access(project_venv_candidate, os.X_OK):
        return str(project_venv_candidate)

    return None


def _local_volttron_ansible_collection_path() -> str | None:
    candidate = Path(__file__).resolve().parents[3] / "volttron-ansible"
    if (candidate / "galaxy.yml").exists() and (candidate / "playbooks" / "install_platform.yml").exists():
        return str(candidate)
    return None


def _expand(path_value: str) -> str:
    return os.path.abspath(os.path.expanduser(path_value))


def _local_python_is_supported() -> bool:
    return sys.version_info[:2] == SUPPORTED_LOCAL_PYTHON


def _should_bootstrap_python(*, is_local: bool, python_interpreter: str) -> bool:
    if (python_interpreter or "").strip().lower() != AUTO_PYTHON_INTERPRETER:
        return False
    return not is_local or not _local_python_is_supported()


def _resolved_python_interpreter(*, is_local: bool, python_interpreter: str) -> str:
    if _should_bootstrap_python(is_local=is_local, python_interpreter=python_interpreter):
        return BOOTSTRAPPED_PYTHON_PATH
    if (python_interpreter or "").strip().lower() == AUTO_PYTHON_INTERPRETER:
        return sys.executable
    return python_interpreter or "python3"


def _ansible_module_python_interpreter(*, is_local: bool) -> str:
    return sys.executable if is_local else "python3"


def _write_sudo_askpass_helper(become_password: str) -> str:
    fd, path = tempfile.mkstemp(prefix="volttron-sudo-askpass-", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write("#!/bin/sh\n")
        file.write("cat <<'EOF'\n")
        file.write(become_password)
        file.write("\nEOF\n")
    os.chmod(path, 0o700)
    return path


def _safe_alias(name: str) -> str:
    alias = re.sub(r"[^A-Za-z0-9_-]+", "-", name.strip())
    alias = alias.strip("-")
    return alias or "volttron-instance"


def _normalize_web_address(address: str, host: str, is_local: bool) -> str:
    if is_local:
        return address

    parsed = urlparse(address)
    if not parsed.hostname or parsed.hostname == "0.0.0.0":
        netloc = host
        if parsed.port:
            netloc = f"{host}:{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))
    return address


async def _run_command(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 1800,
) -> tuple[str, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise AnsibleDeployError(f"Command timed out: {' '.join(args)}") from exc

    stdout_text = stdout.decode(errors="replace") if stdout else ""
    stderr_text = stderr.decode(errors="replace") if stderr else ""
    if process.returncode != 0:
        detail = stderr_text.strip() or stdout_text.strip() or f"exit code {process.returncode}"
        raise AnsibleDeployError(f"{' '.join(args)} failed: {detail}")
    return stdout_text, stderr_text


async def ensure_ansible_ready() -> None:
    missing = [name for name in ("ansible-playbook", "ansible-galaxy") if _find_executable(name) is None]
    if missing:
        raise AnsibleDeployError(
            "Ansible is required for deployment. Install the app requirements again with "
            "`pip install -r requirements.txt`; missing: " + ", ".join(missing)
        )

    ansible_galaxy = _find_executable("ansible-galaxy")
    if not ansible_galaxy:
        raise AnsibleDeployError("Unable to locate ansible-galaxy.")

    collection_source = _local_volttron_ansible_collection_path() or ANSIBLE_COLLECTION_URL
    await _run_command(
        [
            ansible_galaxy,
            "collection",
            "install",
            "-f",
            collection_source,
        ],
        timeout=900,
    )
    await _run_command(
        [
            ansible_galaxy,
            "collection",
            "install",
            "community.general",
        ],
        timeout=600,
    )


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _inventory_host_vars(
    *,
    host_alias: str,
    is_local: bool,
    host: str,
    username: str,
    ssh_port: str | int,
    ssh_key_path: str,
    ignore_host_keys: bool,
    volttron_home: str,
    volttron_venv: str,
    http_proxy: str,
    https_proxy: str,
    python_interpreter: str,
    web_enabled: bool,
    web_bind_address: str,
    web_secret: str,
) -> dict[str, Any]:
    use_managed_python = _should_bootstrap_python(is_local=is_local, python_interpreter=python_interpreter)
    resolved_python_interpreter = _resolved_python_interpreter(
        is_local=is_local,
        python_interpreter=python_interpreter,
    )
    host_vars: dict[str, Any] = {
        "volttron_home": volttron_home,
        "volttron_venv": volttron_venv,
        "volttron_log_file": f"{volttron_home.rstrip('/')}/volttron.log",
        "python_interpreter": resolved_python_interpreter,
        "volttron_bootstrap_python": use_managed_python,
        "volttron_python_version": "3.10",
        "http_proxy": http_proxy or "",
        "https_proxy": https_proxy or "",
        "web_enabled": web_enabled,
        "web_bind_address": web_bind_address,
        "web_secret_key": web_secret,
    }

    if is_local:
        host_vars.update(
            {
                "ansible_connection": "local",
                "ansible_host": "localhost",
                "ansible_user": os.getenv("USER") or os.getenv("LOGNAME") or "root",
                "ansible_python_interpreter": _ansible_module_python_interpreter(is_local=is_local),
            }
        )
        return host_vars

    host_vars.update(
        {
            "ansible_host": host,
            "ansible_user": username,
            "ansible_port": int(ssh_port or 22),
            "ansible_connection": "ssh",
            "ansible_python_interpreter": _ansible_module_python_interpreter(is_local=is_local),
        }
    )
    if ssh_key_path:
        host_vars["ansible_ssh_private_key_file"] = _expand(ssh_key_path)
    if ignore_host_keys:
        host_vars["ansible_ssh_common_args"] = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

    return host_vars


def _platform_config(
    *,
    instance_name: str,
    web_enabled: bool,
    web_bind_address: str,
    web_secret: str,
    web_admin_user: str,
    web_admin_password: str,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "instance-name": instance_name,
        "messagebus": "zmq",
        "auth-enabled": True,
        "server-messagebus-id": "vip.server",
        "agent-monitor-frequency": 600,
        "enable-federation": False,
        "enable-federation-cache": True,
        "web-enabled": web_enabled,
    }
    if web_enabled:
        config.update(
            {
                "bind-web-address": web_bind_address,
                "web-secret-key": web_secret,
                "web-admin-user": web_admin_user,
                "web-admin-password": web_admin_password,
                "web-admin-groups": ["admin", "vui"],
            }
        )
    return {"config": config, "agents": {}}


def prepare_ansible_files(
    *,
    instance_name: str,
    is_local: bool,
    host: str,
    username: str,
    ssh_port: str | int,
    ssh_key_path: str,
    ignore_host_keys: bool,
    volttron_home: str,
    volttron_venv: str,
    web_enabled: bool,
    web_bind_address: str,
    http_proxy: str = "",
    https_proxy: str = "",
    python_interpreter: str = "python3",
    web_admin_user: str = "",
    web_admin_password: str = "",
) -> tuple[Path, Path, str, str]:
    host_alias = _safe_alias(instance_name)
    deployment_dir = ANSIBLE_ROOT / host_alias
    config_root = deployment_dir / "config"
    host_config_dir = config_root / host_alias
    inventory_path = deployment_dir / "inventory.yml"
    web_secret = secrets.token_urlsafe(32)

    inventory = {
        "all": {
            "hosts": {
                host_alias: _inventory_host_vars(
                    host_alias=host_alias,
                    is_local=is_local,
                    host=host,
                    username=username,
                    ssh_port=ssh_port,
                    ssh_key_path=ssh_key_path,
                    ignore_host_keys=ignore_host_keys,
                    volttron_home=volttron_home,
                    volttron_venv=volttron_venv,
                    http_proxy=http_proxy,
                    https_proxy=https_proxy,
                    python_interpreter=python_interpreter,
                    web_enabled=web_enabled,
                    web_bind_address=web_bind_address,
                    web_secret=web_secret,
                )
            },
            "vars": {
                "deployment_config_root": str(config_root.resolve()),
            },
        }
    }
    _write_yaml(inventory_path, inventory)
    _write_yaml(
        host_config_dir / f"{host_alias}.yml",
        _platform_config(
            instance_name=instance_name,
            web_enabled=web_enabled,
            web_bind_address=web_bind_address,
            web_secret=web_secret,
            web_admin_user=web_admin_user,
            web_admin_password=web_admin_password,
        ),
    )
    _write_yaml(deployment_dir / "install_extra_packages.yml", _extra_packages_playbook())
    _write_yaml(deployment_dir / "bootstrap_python.yml", _bootstrap_python_playbook())
    _write_yaml(deployment_dir / "prepare_ansible_venv.yml", _prepare_ansible_venv_playbook())
    return inventory_path, config_root, host_alias, web_secret


def _bootstrap_python_playbook() -> list[dict[str, Any]]:
    # TODO: Upstream this into volttron-ansible as a Python runtime/bootstrap role.
    # New Ubuntu releases can ship Python versions ahead of VOLTTRON dependency support,
    # so users should not have to manually install Python 3.10 before deployment.
    return [{
        "name": "bootstrap supported Python for VOLTTRON",
        "hosts": "{{ on_hosts | default('all') }}",
        "gather_facts": True,
        "tasks": [
            {
                "name": "Install uv prerequisites on apt systems",
                "ansible.builtin.apt": {
                    "name": [
                        "ca-certificates",
                        "curl",
                    ],
                    "state": "present",
                    "update_cache": True,
                },
                "become": True,
                "when": "ansible_os_family == 'Debian'",
            },
            {
                "name": "Install uv for managed Python runtimes",
                "ansible.builtin.shell": (
                    "set -eu\n"
                    "if [ ! -x \"$HOME/.local/bin/uv\" ]; then\n"
                    "  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
                    "fi\n"
                ),
                "args": {
                    "executable": "/bin/bash",
                    "creates": "{{ ansible_env.HOME }}/.local/bin/uv",
                },
                "environment": {
                    "http_proxy": "{{ http_proxy | default('') }}",
                    "https_proxy": "{{ https_proxy | default('') }}",
                },
            },
            {
                "name": "Install supported Python runtime",
                "ansible.builtin.command": (
                    "{{ ansible_env.HOME }}/.local/bin/uv python install "
                    "{{ volttron_python_version | default('3.10') }}"
                ),
                "environment": {
                    "http_proxy": "{{ http_proxy | default('') }}",
                    "https_proxy": "{{ https_proxy | default('') }}",
                },
                "changed_when": False,
            },
            {
                "name": "Find managed Python runtime",
                "ansible.builtin.command": (
                    "{{ ansible_env.HOME }}/.local/bin/uv python find "
                    "{{ volttron_python_version | default('3.10') }}"
                ),
                "register": "volttron_managed_python",
                "changed_when": False,
            },
            {
                "name": "Create stable VOLTTRON Python link",
                "ansible.builtin.file": {
                    "src": "{{ volttron_managed_python.stdout }}",
                    "dest": "{{ python_interpreter }}",
                    "state": "link",
                    "force": True,
                },
            },
            {
                "name": "Verify managed Python version",
                "ansible.builtin.command": "{{ python_interpreter }} --version",
                "register": "volttron_python_version_check",
                "changed_when": False,
            },
            {
                "name": "Show managed Python version",
                "ansible.builtin.debug": {
                    "msg": "{{ volttron_python_version_check.stdout }} at {{ python_interpreter }}",
                },
            },
        ],
    }]


def _prepare_ansible_venv_playbook() -> list[dict[str, Any]]:
    return [{
        "name": "prepare remote Ansible module venv",
        "hosts": "{{ on_hosts | default('all') }}",
        "tasks": [
            {
                "name": "Create Ansible module venv dependencies",
                "ansible.builtin.pip": {
                    "virtualenv": "{{ venv_for_ansible | default(ansible_env.HOME + '/ansible_venv') }}",
                    "virtualenv_command": "{{ python_interpreter | default('python3') }} -m venv",
                    "name": [
                        "packaging",
                        "pexpect",
                    ],
                },
                "environment": {
                    "http_proxy": "{{ http_proxy | default('') }}",
                    "https_proxy": "{{ https_proxy | default('') }}",
                },
            }
        ],
    }]


def _extra_packages_playbook() -> dict[str, Any]:
    return [{
        "name": "install extra modular VOLTTRON packages",
        "hosts": "{{ on_hosts | default('all') }}",
        "tasks": [
            {
                "name": "Install extra packages into VOLTTRON venv",
                "ansible.builtin.pip": {
                    "virtualenv": "{{ volttron_venv }}",
                    "virtualenv_command": "{{ python_interpreter | default('python3') }} -m venv",
                    "name": "{{ extra_volttron_packages }}",
                },
                "environment": {
                    "http_proxy": "{{ http_proxy | default('') }}",
                    "https_proxy": "{{ https_proxy | default('') }}",
                },
                "when": "extra_volttron_packages | default([]) | length > 0",
            }
        ],
    }]

async def _run_playbook(
    inventory_path: Path,
    playbook: str,
    host_alias: str,
    *,
    extra_vars: dict[str, Any] | None = None,
    become_password: str = "",
    local_sudo_askpass: bool = False,
    timeout: int = 1800,
) -> tuple[str, str]:
    combined_extra_vars = {"on_hosts": host_alias}
    if extra_vars:
        combined_extra_vars.update(extra_vars)
    askpass_path = ""
    if local_sudo_askpass:
        if not become_password:
            raise AnsibleDeployError(
                "Local deployment needs sudo for Ubuntu package setup and systemd service management. "
                "Enter your sudo password in Advanced Settings; it is used only for this deployment and is not saved."
            )
        askpass_path = _write_sudo_askpass_helper(become_password)
        combined_extra_vars["ansible_become_method"] = "sudo"
        combined_extra_vars["ansible_become_flags"] = "-H -A"
    elif become_password:
        combined_extra_vars["ansible_become_pass"] = become_password
        combined_extra_vars["ansible_sudo_pass"] = become_password

    args = [
        _find_executable("ansible-playbook") or "ansible-playbook",
        "-i",
        str(inventory_path),
        playbook,
        "--extra-vars",
        json.dumps(combined_extra_vars),
    ]
    env = os.environ.copy()
    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    if askpass_path:
        env["SUDO_ASKPASS"] = askpass_path
    try:
        return await _run_command(args, env=env, timeout=timeout)
    finally:
        if askpass_path:
            try:
                os.remove(askpass_path)
            except FileNotFoundError:
                pass


async def deploy_with_ansible(
    *,
    instance_name: str,
    is_local: bool,
    host: str,
    username: str,
    ssh_port: str | int,
    ssh_key_path: str,
    ignore_host_keys: bool,
    volttron_home: str,
    volttron_venv: str,
    web_enabled: bool,
    web_bind_address: str,
    extra_packages: list[str],
    become_password: str = "",
    http_proxy: str = "",
    https_proxy: str = "",
    python_interpreter: str = "python3",
) -> AnsibleDeploymentResult:
    await ensure_ansible_ready()

    web_credentials: dict[str, str] = {}
    web_admin_user = ""
    web_admin_password = ""
    if web_enabled:
        web_admin_user = "volttron-installer"
        web_admin_password = secrets.token_urlsafe(16)
        web_credentials = {
            "web_admin_user": web_admin_user,
            "web_admin_pass": web_admin_password,
            "web_bind_address": _normalize_web_address(web_bind_address, host, is_local),
            "web_listen_address": web_bind_address,
        }

    inventory_path, config_root, host_alias, _ = prepare_ansible_files(
        instance_name=instance_name,
        is_local=is_local,
        host=host,
        username=username,
        ssh_port=ssh_port,
        ssh_key_path=ssh_key_path,
        ignore_host_keys=ignore_host_keys,
        volttron_home=volttron_home,
        volttron_venv=volttron_venv,
        web_enabled=web_enabled,
        web_bind_address=web_bind_address,
        http_proxy=http_proxy,
        https_proxy=https_proxy,
        python_interpreter=python_interpreter,
        web_admin_user=web_admin_user,
        web_admin_password=web_admin_password,
    )

    if is_local:
        generated_inventory = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
        generated_host = generated_inventory["all"]["hosts"][host_alias]
        if generated_host.get("ansible_python_interpreter") != sys.executable:
            raise AnsibleDeployError(
                "Local Ansible inventory was generated with the wrong control Python. "
                f"Expected {sys.executable}, got {generated_host.get('ansible_python_interpreter')}."
            )

    if _should_bootstrap_python(is_local=is_local, python_interpreter=python_interpreter):
        await _run_playbook(
            inventory_path,
            str((inventory_path.parent / "bootstrap_python.yml").resolve()),
            host_alias,
            become_password=become_password,
            local_sudo_askpass=is_local and bool(become_password),
            timeout=900,
        )

    await _run_playbook(
        inventory_path,
        str((inventory_path.parent / "prepare_ansible_venv.yml").resolve()),
        host_alias,
        become_password=become_password,
        local_sudo_askpass=is_local and bool(become_password),
        timeout=600,
    )

    await _run_playbook(
        inventory_path,
        "volttron.deployment.install_platform",
        host_alias,
        become_password=become_password,
        local_sudo_askpass=is_local and bool(become_password),
        timeout=2400,
    )

    if extra_packages:
        await _run_playbook(
            inventory_path,
            str((inventory_path.parent / "install_extra_packages.yml").resolve()),
            host_alias,
            extra_vars={"extra_volttron_packages": extra_packages},
            become_password=become_password,
            local_sudo_askpass=is_local and bool(become_password),
            timeout=1200,
        )

    await _run_playbook(
        inventory_path,
        "volttron.deployment.run_platforms",
        host_alias,
        become_password=become_password,
        local_sudo_askpass=is_local and bool(become_password),
        timeout=600,
    )

    return AnsibleDeploymentResult(
        inventory_path=inventory_path,
        config_root=config_root,
        host_alias=host_alias,
        web_credentials=web_credentials,
    )
