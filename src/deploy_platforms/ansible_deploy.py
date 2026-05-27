import asyncio
import json
import os
import re
import secrets
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import yaml


ANSIBLE_COLLECTION_URL = "git+https://github.com/eclipse-volttron/volttron-ansible.git,develop"
ANSIBLE_ROOT = Path("ansible_deployments")
AUTO_PYTHON_INTERPRETER = "auto"
BOOTSTRAPPED_PYTHON_PATH = "{{ ansible_env.HOME }}/.local/bin/volttron-python3.10"


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


def _expand(path_value: str) -> str:
    return os.path.abspath(os.path.expanduser(path_value))


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

    await _run_command(
        [
            ansible_galaxy,
            "collection",
            "install",
            "-f",
            ANSIBLE_COLLECTION_URL,
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
    host_vars: dict[str, Any] = {
        "volttron_home": volttron_home,
        "volttron_venv": volttron_venv,
        "volttron_log_file": f"{volttron_home.rstrip('/')}/volttron.log",
        "python_interpreter": BOOTSTRAPPED_PYTHON_PATH
        if (python_interpreter or "").strip().lower() == AUTO_PYTHON_INTERPRETER
        else (python_interpreter or "python3"),
        "volttron_bootstrap_python": (python_interpreter or "").strip().lower() == AUTO_PYTHON_INTERPRETER,
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
                "ansible_python_interpreter": sys.executable,
            }
        )
        return host_vars

    host_vars.update(
        {
            "ansible_host": host,
            "ansible_user": username,
            "ansible_port": int(ssh_port or 22),
            "ansible_connection": "ssh",
            "ansible_python_interpreter": "python3",
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
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "instance-name": instance_name,
        "messagebus": "zmq",
        "auth-enabled": True,
        "server-messagebus-id": "vip.server",
        "agent-monitor-frequency": 600,
        "enable-federation": False,
        "enable-federation-cache": True,
    }
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
        ),
    )
    _write_yaml(deployment_dir / "install_extra_packages.yml", _extra_packages_playbook())
    _write_yaml(deployment_dir / "configure_web_service.yml", _configure_web_service_playbook())
    _write_yaml(deployment_dir / "setup_web_user.yml", _web_user_playbook())
    _write_yaml(deployment_dir / "bootstrap_python.yml", _bootstrap_python_playbook())
    _write_yaml(deployment_dir / "prepare_ansible_venv.yml", _prepare_ansible_venv_playbook())
    _write_yaml(deployment_dir / "start_systemd_service.yml", _start_systemd_playbook())
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
                        "psutil",
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


def _configure_web_service_playbook() -> list[dict[str, Any]]:
    # TODO: Replace this installer shim when volttron-ansible configures the modular
    # PlatformWebService section directly. The web service currently expects [web]
    # bind-web-address and web-secret-key rather than [volttron] bind-web-address.
    return [{
        "name": "configure VOLTTRON web service",
        "hosts": "{{ on_hosts | default('all') }}",
        "tasks": [
            {
                "name": "Configure web bind address",
                "ansible.builtin.ini_file": {
                    "path": "{{ volttron_home }}/config",
                    "section": "web",
                    "option": "bind-web-address",
                    "value": "{{ web_bind_address }}",
                    "mode": "0600",
                },
                "when": "web_enabled | bool",
            },
            {
                "name": "Configure web secret key",
                "ansible.builtin.ini_file": {
                    "path": "{{ volttron_home }}/config",
                    "section": "web",
                    "option": "web-secret-key",
                    "value": "{{ web_secret_key }}",
                    "mode": "0600",
                },
                "when": "web_enabled | bool",
                "no_log": True,
            },
        ],
    }]


def _web_user_playbook() -> list[dict[str, Any]]:
    return [{
        "name": "setup VOLTTRON web user",
        "hosts": "{{ on_hosts | default('all') }}",
        "tasks": [
            {
                "name": "Ensure VOLTTRON_HOME exists",
                "ansible.builtin.file": {
                    "path": "{{ volttron_home }}",
                    "state": "directory",
                    "mode": "0755",
                },
            },
            {
                "name": "Copy web user setup script",
                "ansible.builtin.copy": {
                    "dest": "{{ volttron_home }}/installer_setup_web_user.py",
                    "mode": "0600",
                    "content": WEB_USER_SCRIPT,
                },
            },
            {
                "name": "Create installer web user",
                "ansible.builtin.command": (
                    "{{ volttron_venv }}/bin/python {{ volttron_home }}/installer_setup_web_user.py"
                ),
                "environment": {
                    "INSTALLER_WEB_USER": "{{ installer_web_user }}",
                    "INSTALLER_WEB_PASSWORD": "{{ installer_web_password }}",
                    "VOLTTRON_HOME": "{{ volttron_home }}",
                },
                "changed_when": True,
            },
            {
                "name": "Remove web user setup script",
                "ansible.builtin.file": {
                    "path": "{{ volttron_home }}/installer_setup_web_user.py",
                    "state": "absent",
                },
            },
        ],
    }]


def _start_systemd_playbook() -> list[dict[str, Any]]:
    # TODO: Switch back to volttron.deployment.run_platforms after its systemd path
    # verifies service state with systemctl instead of relying on the legacy
    # VOLTTRON_PID file check.
    return [{
        "name": "start VOLTTRON systemd service",
        "hosts": "{{ on_hosts | default('all') }}",
        "roles": [
            "volttron.deployment.set_defaults",
        ],
        "tasks": [
            {
                "name": "Start and enable VOLTTRON service",
                "ansible.builtin.systemd_service": {
                    "name": "volttron-{{ instance_name }}",
                    "state": "started",
                    "enabled": True,
                    "daemon_reload": True,
                },
                "become": True,
            }
        ],
    }]


WEB_USER_SCRIPT = r"""import json
import os
from pathlib import Path

from passlib.hash import argon2
import zmq

volttron_home = Path(os.environ["VOLTTRON_HOME"]).expanduser()
volttron_home.mkdir(parents=True, exist_ok=True)
username = os.environ["INSTALLER_WEB_USER"]
password = os.environ["INSTALLER_WEB_PASSWORD"]

users_file = volttron_home / "web-users.json"
users = json.loads(users_file.read_text()) if users_file.exists() else {}
users[username] = {
    "hashed_password": argon2.hash(password),
    "groups": ["admin", "vui"],
}
users_file.write_text(json.dumps(users, indent=2))

creds_dir = volttron_home / "credentials_store"
creds_dir.mkdir(exist_ok=True)
creds_file = creds_dir / "platform.web.json"
if not creds_file.exists():
    publickey, secretkey = [key.decode("ascii") for key in zmq.curve_keypair()]
    creds_file.write_text(json.dumps({
        "identity": "platform.web",
        "publickey": publickey,
        "secretkey": secretkey,
        "domain": "",
        "address": "",
    }, indent=2))

authz_file = volttron_home / "authz.json"
authz_data = json.loads(authz_file.read_text()) if authz_file.exists() else {
    "roles": {},
    "agents": {},
    "agent_groups": {},
}
authz_data.setdefault("roles", {})
authz_data.setdefault("agents", {})
authz_data.setdefault("agent_groups", {})
authz_data["agents"].setdefault("platform.web", {
    "comments": "Automatically added by VOLTTRON Installer for web service"
})

admin_users = authz_data["agent_groups"].setdefault("admin_users", {})
identities = set(admin_users.get("identities", []))
identities.add("platform.web")
admin_users["identities"] = sorted(identities)
roles = set(admin_users.get("agent_roles", []))
roles.add("admin")
admin_users["agent_roles"] = sorted(roles)
authz_file.write_text(json.dumps(authz_data, indent=2))
print("INSTALLER_WEB_USER_READY")
"""


async def _run_playbook(
    inventory_path: Path,
    playbook: str,
    host_alias: str,
    *,
    extra_vars: dict[str, Any] | None = None,
    become_password: str = "",
    timeout: int = 1800,
) -> tuple[str, str]:
    combined_extra_vars = {"on_hosts": host_alias}
    if extra_vars:
        combined_extra_vars.update(extra_vars)
    if become_password:
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
    return await _run_command(args, env=env, timeout=timeout)


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
    )

    if (python_interpreter or "").strip().lower() == AUTO_PYTHON_INTERPRETER:
        await _run_playbook(
            inventory_path,
            str((inventory_path.parent / "bootstrap_python.yml").resolve()),
            host_alias,
            become_password=become_password,
            timeout=900,
        )

    await _run_playbook(
        inventory_path,
        str((inventory_path.parent / "prepare_ansible_venv.yml").resolve()),
        host_alias,
        become_password=become_password,
        timeout=600,
    )

    await _run_playbook(
        inventory_path,
        "volttron.deployment.install_platform",
        host_alias,
        become_password=become_password,
        timeout=2400,
    )

    if extra_packages:
        await _run_playbook(
            inventory_path,
            str((inventory_path.parent / "install_extra_packages.yml").resolve()),
            host_alias,
            extra_vars={"extra_volttron_packages": extra_packages},
            become_password=become_password,
            timeout=1200,
        )

    if web_enabled:
        await _run_playbook(
            inventory_path,
            str((inventory_path.parent / "configure_web_service.yml").resolve()),
            host_alias,
            become_password=become_password,
            timeout=300,
        )

    web_credentials: dict[str, str] = {}
    if web_enabled:
        username_value = "volttron-installer"
        password_value = secrets.token_urlsafe(16)
        await _run_playbook(
            inventory_path,
            str((inventory_path.parent / "setup_web_user.yml").resolve()),
            host_alias,
            extra_vars={
                "installer_web_user": username_value,
                "installer_web_password": password_value,
            },
            become_password=become_password,
            timeout=300,
        )
        web_credentials = {
            "web_admin_user": username_value,
            "web_admin_pass": password_value,
            "web_bind_address": _normalize_web_address(web_bind_address, host, is_local),
            "web_listen_address": web_bind_address,
        }

    await _run_playbook(
        inventory_path,
        str((inventory_path.parent / "start_systemd_service.yml").resolve()),
        host_alias,
        become_password=become_password,
        timeout=600,
    )

    return AnsibleDeploymentResult(
        inventory_path=inventory_path,
        config_root=config_root,
        host_alias=host_alias,
        web_credentials=web_credentials,
    )
