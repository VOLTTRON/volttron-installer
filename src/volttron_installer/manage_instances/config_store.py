import json
from urllib.parse import quote

import httpx


class ConfigStoreError(Exception):
    pass


def _base_url(instance: dict) -> str:
    web_address = instance.get("web_bind_address", "")
    if not web_address:
        raise ConfigStoreError("No web API address is configured for this instance.")
    return web_address.rstrip("/")


async def _access_token(instance: dict, client: httpx.AsyncClient) -> str:
    username = instance.get("web_admin_user", "")
    password = instance.get("web_admin_pass", "")
    if not username or not password:
        raise ConfigStoreError("No web admin credentials are configured for this instance.")

    response = await client.post(
        f"{_base_url(instance)}/authenticate",
        json={"username": username, "password": password},
    )
    if response.status_code >= 400:
        raise ConfigStoreError(f"Authentication failed: HTTP {response.status_code} {response.text}")

    token = response.json().get("access_token")
    if not token:
        raise ConfigStoreError("Authentication response did not include an access token.")
    return token


def _agent_configs_url(instance: dict, agent_identity: str, config_name: str | None = None) -> str:
    platform = quote(instance.get("name", ""), safe="")
    agent = quote(agent_identity, safe="")
    url = f"{_base_url(instance)}/vui/platforms/{platform}/agents/{agent}/configs"
    if config_name:
        url += f"/{quote(config_name, safe='')}"
    return url


def _config_store_rpc_url(instance: dict, method_name: str) -> str:
    platform = quote(instance.get("name", ""), safe="")
    return f"{_base_url(instance)}/vui/platforms/{platform}/agents/platform.config_store/rpc/{quote(method_name, safe='')}"


def _packaged_configs_url(instance: dict) -> str:
    platform = quote(instance.get("name", ""), safe="")
    return f"{_base_url(instance)}/vui/platforms/{platform}/packaged-configs"


def _raise_for_api_error(response: httpx.Response, action: str) -> None:
    if response.status_code < 400:
        return
    try:
        payload = response.json()
        detail = payload.get("error") or payload.get("Error") or payload
    except Exception:
        detail = response.text
    raise ConfigStoreError(f"{action} failed: HTTP {response.status_code} {detail}")


async def list_configs(instance: dict, agent_identity: str) -> list[str]:
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        token = await _access_token(instance, client)
        response = await client.post(
            _config_store_rpc_url(instance, "list_configs"),
            headers={"Authorization": f"BEARER {token}"},
            json={"args": [agent_identity]},
        )
        _raise_for_api_error(response, "List configs")
        payload = response.json()
        if isinstance(payload, list):
            return sorted(str(item) for item in payload)
        links = payload.get("links") or payload.get("route_options") or {}
        if isinstance(links, dict):
            return sorted(links.keys())
        return []


async def list_packaged_configs(instance: dict) -> dict:
    """Return example configs exposed by packages installed in the instance venv."""
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        token = await _access_token(instance, client)
        response = await client.get(
            _packaged_configs_url(instance),
            headers={"Authorization": f"BEARER {token}"},
        )
        _raise_for_api_error(response, "List packaged configs")
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


async def get_config(instance: dict, agent_identity: str, config_name: str) -> tuple[str, str]:
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        token = await _access_token(instance, client)
        response = await client.post(
            _config_store_rpc_url(instance, "get_config"),
            headers={"Authorization": f"BEARER {token}"},
            json={"args": [agent_identity, config_name, True]},
        )
        _raise_for_api_error(response, "Get config")
        raw_content = response.json()
        metadata_response = await client.post(
            _config_store_rpc_url(instance, "get_metadata"),
            headers={"Authorization": f"BEARER {token}"},
            json={"args": [agent_identity, config_name]},
        )
        content_type = "application/json"
        if metadata_response.status_code < 400:
            metadata = metadata_response.json()
            config_type = metadata.get("type") if isinstance(metadata, dict) else None
            content_type = {
                "json": "application/json",
                "csv": "text/csv",
                "raw": "text/plain",
            }.get(config_type, "application/json")
        if isinstance(raw_content, (dict, list)):
            return json.dumps(raw_content, indent=2), content_type
        return str(raw_content), content_type


async def save_config(
    instance: dict,
    agent_identity: str,
    config_name: str,
    content: str,
    content_type: str,
    overwrite: bool,
) -> None:
    if not config_name.strip():
        raise ConfigStoreError("Config name is required.")
    if content_type not in {"application/json", "text/csv", "text/plain"}:
        raise ConfigStoreError("Config type must be JSON, CSV, or raw text.")

    method = "PUT" if overwrite else "POST"
    url = _agent_configs_url(instance, agent_identity, config_name if overwrite else None)
    params = None if overwrite else {"config-name": config_name}

    kwargs = {"content": content}
    if content_type == "application/json":
        try:
            kwargs = {"json": json.loads(content or "{}")}
        except json.JSONDecodeError as exc:
            raise ConfigStoreError(f"Invalid JSON: {exc}") from exc

    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        token = await _access_token(instance, client)
        response = await client.post(
            _config_store_rpc_url(instance, "set_config"),
            headers={"Authorization": f"BEARER {token}"},
            json={
                "args": [
                    agent_identity,
                    config_name,
                    content,
                    {"application/json": "json", "text/csv": "csv", "text/plain": "raw"}[content_type],
                ]
            },
        )
        _raise_for_api_error(response, "Save config")


async def delete_config(instance: dict, agent_identity: str, config_name: str) -> None:
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        token = await _access_token(instance, client)
        response = await client.post(
            _config_store_rpc_url(instance, "delete_config"),
            headers={"Authorization": f"BEARER {token}"},
            json={"args": [agent_identity, config_name]},
        )
        _raise_for_api_error(response, "Delete config")


async def delete_all_configs(instance: dict, agent_identity: str) -> None:
    for config_name in await list_configs(instance, agent_identity):
        await delete_config(instance, agent_identity, config_name)

    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        token = await _access_token(instance, client)
        response = await client.post(
            _config_store_rpc_url(instance, "delete_store"),
            headers={"Authorization": f"BEARER {token}"},
            json={"args": [agent_identity]},
        )
        if response.status_code not in {204, 400, 404}:
            _raise_for_api_error(response, "Delete config store")
