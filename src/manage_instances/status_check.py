import httpx
import os
import socket
from urllib.parse import urlparse

def is_port_bound(host: str, port: int) -> bool:
    """
    Checks if a TCP port is bound and listening. 
    Useful for checking VOLTTRON VIP connections when the web server isn't enabled.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        # connect_ex returns 0 if the connection is successful (port bound/open)
        result = s.connect_ex((host, port))
    return result == 0


def is_local_volttron_process_running(volttron_home: str | None) -> bool:
    """
    Check for a local VOLTTRON process that belongs to this exact instance.

    Web ports can collide across local instances, so a generic HTTP response on
    8443 is not enough to identify which platform is running. The launched
    command includes this instance's volttron.log path, and VOLTTRON_HOME is
    exported into the process environment, so either match is instance-specific.
    """
    if not volttron_home:
        return False

    expanded_home = os.path.abspath(os.path.expanduser(volttron_home))
    expected_log = os.path.join(expanded_home, "volttron.log")

    proc_dir = "/proc"
    if not os.path.isdir(proc_dir):
        return False

    for pid in os.listdir(proc_dir):
        if not pid.isdigit():
            continue
        try:
            with open(os.path.join(proc_dir, pid, "cmdline"), "rb") as file:
                cmdline = file.read().replace(b"\x00", b" ").decode(errors="ignore")
            if "volttron" not in cmdline:
                continue
            if expected_log in cmdline:
                return True

            with open(os.path.join(proc_dir, pid, "environ"), "rb") as file:
                environ = file.read().decode(errors="ignore")
            if f"VOLTTRON_HOME={expanded_home}" in environ:
                return True
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue

    return False

async def check_platform_web_status(web_address: str) -> dict:
    """
    Checks the status of the VOLTTRON platform via its web API /discovery/ endpoint.
    Returns a dict with 'status' (online/offline) and optionally the discovery payload.
    """
    if not web_address:
        return {"status": "offline", "message": "No web address configured"}
        
    discovery_url = web_address.rstrip('/') + "/index.html"
    
    # We use verify=False because the installer uses self-signed certs by default
    async with httpx.AsyncClient(verify=False, timeout=3.0) as client:
        try:
            response = await client.get(discovery_url)
            if response.status_code == 200:
                return {"status": "online", "message": "Web server is up"}
            else:
                return {"status": "offline", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "offline", "message": str(e)}


async def check_volttron_rest_status(instance: dict) -> dict:
    """
    Checks whether VOLTTRON is running through the web API control plane.

    A successful response from /vui/platforms/{instance}/status means the web
    service is alive and can RPC into the platform control service. This is the
    preferred status signal for local and future remote deployments.
    """
    if instance.get("is_local") and not is_local_volttron_process_running(instance.get("volttron_home")):
        return {"status": "stopped", "message": "No local VOLTTRON process found for this instance"}

    web_address = instance.get("web_bind_address", "")
    if not web_address:
        return {"status": "unknown", "message": "No web address configured"}

    username = instance.get("web_admin_user", "")
    password = instance.get("web_admin_pass", "")
    if not username or not password:
        return {"status": "unknown", "message": "No web admin credentials configured"}

    base_url = web_address.rstrip("/")
    platform_name = instance.get("name", "")

    timeout = httpx.Timeout(3.0, connect=1.0)
    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        try:
            auth_response = await client.post(
                f"{base_url}/authenticate",
                json={"username": username, "password": password},
            )
            if auth_response.status_code == 401:
                return {"status": "running", "message": "Web API is up, but credentials were rejected"}
            if auth_response.status_code >= 500:
                if instance.get("is_local"):
                    return {"status": "running", "message": f"Local VOLTTRON process is running; web authentication returned HTTP {auth_response.status_code}"}
                return {"status": "unknown", "message": f"Authentication HTTP {auth_response.status_code}"}
            if auth_response.status_code >= 400:
                return {"status": "unknown", "message": f"Authentication HTTP {auth_response.status_code}"}

            access_token = auth_response.json().get("access_token")
            if not access_token:
                return {"status": "unknown", "message": "Authentication response did not include an access token"}

            status_response = await client.get(
                f"{base_url}/vui/platforms/{platform_name}/status",
                headers={"Authorization": f"BEARER {access_token}"},
            )
            if status_response.status_code == 200:
                return {
                    "status": "running",
                    "message": "VOLTTRON status endpoint responded",
                    "agents": status_response.json(),
                }
            if status_response.status_code >= 500:
                return {"status": "running", "message": f"Web API is up, but platform status returned HTTP {status_response.status_code}"}
            if status_response.status_code in {400, 404}:
                return {"status": "unknown", "message": f"Platform status HTTP {status_response.status_code}"}
            return {"status": "stopped", "message": f"Platform status HTTP {status_response.status_code}"}
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
            return {"status": "stopped", "message": "Web API is not reachable"}
        except Exception as e:
            return {"status": "unknown", "message": str(e)}
