import json
import secrets
import shlex

from src import ssh_remote


async def create_remote_venv(instance: dict, venv_path: str) -> str:
    expanded_path = await ssh_remote.expand_path(instance, venv_path)
    await ssh_remote.run(
        instance,
        f"python3 -m venv {shlex.quote(expanded_path)}",
        timeout=300,
    )
    return expanded_path


async def install_remote_packages(instance: dict, venv_path: str, packages: list[str]) -> str:
    expanded_venv = await ssh_remote.expand_path(instance, venv_path)
    pip_executable = f"{expanded_venv}/bin/pip"
    output = ""
    for package in packages:
        args = " ".join(shlex.quote(part) for part in package.split(" "))
        stdout, stderr = await ssh_remote.run(
            instance,
            f"test -x {shlex.quote(pip_executable)} && {shlex.quote(pip_executable)} install {args}",
            timeout=900,
        )
        output = stdout or stderr
    return output


async def configure_remote_volttron(
    instance: dict,
    venv_path: str,
    volttron_home: str,
    instance_name: str,
    web_enabled: bool = True,
    web_bind_address: str = "http://0.0.0.0:8443",
) -> dict:
    expanded_venv = await ssh_remote.expand_path(instance, venv_path)
    expanded_home = await ssh_remote.expand_path(instance, volttron_home)
    await ssh_remote.run(instance, f"mkdir -p {shlex.quote(expanded_home)}", timeout=30)

    web_config = ""
    web_creds = {}
    if web_enabled:
        web_secret = secrets.token_urlsafe(32)
        web_config = f"""
[web]
bind-web-address = {web_bind_address}
web-secret-key = {web_secret}
"""

    config_content = f"""[volttron]
instance-name = {instance_name}
auth-enabled = True
server-messagebus-id = vip.server
agent-monitor-frequency = 600
enable-federation = False
enable-federation-cache = True
{web_config}"""
    await ssh_remote.write_text(instance, f"{expanded_home}/config", config_content)

    pyproject_content = """[tool.poetry]
name = "volttron-runtime"
version = "0.1.0"
description = "VOLTTRON installer runtime project"
authors = ["volttron <volttron@pnnl.gov>"]

[tool.poetry.dependencies]
python = ">=3.10,<3.11"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
"""
    await ssh_remote.write_text(instance, f"{expanded_home}/pyproject.toml", pyproject_content)

    if web_enabled:
        username = "volttron-installer"
        password = secrets.token_urlsafe(16)
        users_payload = json.dumps({"username": username, "password": password, "home": expanded_home})
        script = f"""
import json
from pathlib import Path
from passlib.hash import argon2
import zmq

payload = json.loads({users_payload!r})
volttron_home = Path(payload["home"])
users_file = volttron_home / "web-users.json"

if users_file.exists():
    users = json.loads(users_file.read_text())
else:
    users = {{}}

users[payload["username"]] = {{
    "hashed_password": argon2.hash(payload["password"]),
    "groups": ["admin", "vui"],
}}
users_file.write_text(json.dumps(users, indent=2))

creds_dir = volttron_home / "credentials_store"
creds_dir.mkdir(exist_ok=True)
creds_file = creds_dir / "platform.web.json"
if not creds_file.exists():
    publickey, secretkey = [key.decode("ascii") for key in zmq.curve_keypair()]
    creds_file.write_text(json.dumps({{
        "identity": "platform.web",
        "publickey": publickey,
        "secretkey": secretkey,
        "domain": "",
        "address": ""
    }}, indent=2))

authz_file = volttron_home / "authz.json"
if authz_file.exists():
    authz_data = json.loads(authz_file.read_text())
else:
    authz_data = {{"roles": {{}}, "agents": {{}}, "agent_groups": {{}}}}

authz_data.setdefault("roles", {{}})
authz_data.setdefault("agents", {{}})
authz_data.setdefault("agent_groups", {{}})
authz_data["agents"].setdefault("platform.web", {{
    "comments": "Automatically added by VOLTTRON Installer for web service"
}})

admin_users = authz_data["agent_groups"].setdefault("admin_users", {{}})
identities = set(admin_users.get("identities", []))
identities.add("platform.web")
admin_users["identities"] = sorted(list(identities))
roles = set(admin_users.get("agent_roles", []))
roles.add("admin")
admin_users["agent_roles"] = sorted(list(roles))

authz_file.write_text(json.dumps(authz_data, indent=2))
print("INSTALLER_WEB_USER_READY")
"""
        temp_script = f"{expanded_home}/temp_setup_web_user.py"
        await ssh_remote.write_text(instance, temp_script, script)
        python_exec = f"{expanded_venv}/bin/python"
        try:
            await ssh_remote.run(instance, f"{shlex.quote(python_exec)} {shlex.quote(temp_script)}", timeout=120)
        finally:
            await ssh_remote.run(instance, f"rm -f {shlex.quote(temp_script)}", timeout=30)

        web_creds = {
            "web_admin_user": username,
            "web_admin_pass": password,
            "web_bind_address": web_bind_address.replace("0.0.0.0", instance.get("host", "localhost")),
            "web_listen_address": web_bind_address,
        }

    return web_creds
