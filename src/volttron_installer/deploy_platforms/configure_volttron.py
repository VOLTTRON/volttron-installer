import os
import json
import secrets
import asyncio

async def configure_volttron(
    venv_path: str,
    volttron_home: str,
    instance_name: str,
    web_enabled: bool = True,
    web_bind_address: str = "http://127.0.0.1:8443",
):
    """
    Pre-creates the VOLTTRON config file and sets up a dedicated web user.
    This replicates the old installer's _helpers logic for modular deployments.
    """
    expanded_venv = os.path.expanduser(venv_path)
    expanded_home = os.path.expanduser(volttron_home)
    
    os.makedirs(expanded_home, exist_ok=True)
    
    config_path = os.path.join(expanded_home, 'config')
    
    web_config = ""
    web_creds = {}
    
    if web_enabled:
        web_secret = secrets.token_urlsafe(32)
        bind_address = web_bind_address
        web_config = f"""
[web]
bind-web-address = {bind_address}
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

    with open(config_path, 'w') as f:
        f.write(config_content)
        
    pyproject_path = os.path.join(expanded_home, 'pyproject.toml')
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
    with open(pyproject_path, 'w') as f:
        f.write(pyproject_content)
        
    if web_enabled:
        username = "volttron-installer"
        password = secrets.token_urlsafe(16)
        
        # We run a small script inside the venv to hash the password properly using passlib/argon2
        # which are installed as dependencies of volttron-lib-web.
        script = f"""
import json
import os
from pathlib import Path
from passlib.hash import argon2
import zmq

volttron_home = Path("{expanded_home}")
users_file = volttron_home / "web-users.json"

if users_file.exists():
    users = json.loads(users_file.read_text())
else:
    users = {{}}

users["{username}"] = {{
    "hashed_password": argon2.hash("{password}"),
    "groups": ["admin", "vui"],
}}
users_file.write_text(json.dumps(users, indent=2))

# Generate platform.web.json credentials
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

# Generate authz.json for platform.web
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
        temp_script = os.path.join(expanded_home, 'temp_setup_web_user.py')
        with open(temp_script, 'w') as f:
            f.write(script)
            
        python_exec = os.path.join(expanded_venv, 'bin', 'python')
        
        process = await asyncio.create_subprocess_exec(
            python_exec, temp_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Failed to setup web user: {stderr.decode()}")
            
        os.remove(temp_script)
        
        web_creds = {
            "web_admin_user": username,
            "web_admin_pass": password,
            "web_bind_address": bind_address
        }
    
    return web_creds
