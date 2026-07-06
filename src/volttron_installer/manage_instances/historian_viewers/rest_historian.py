"""
REST data client for the VOLTTRON historian viewer.

Queries historian time-series data through the volttron-lib-web VUI REST API
rather than downloading raw database files.  Auth pattern mirrors config_store.py.
"""

from urllib.parse import quote

import httpx


class HistorianViewerError(Exception):
    pass


def _base_url(instance: dict) -> str:
    web_address = instance.get("web_bind_address", "")
    if not web_address:
        raise HistorianViewerError(
            "No web API address is configured for this instance. "
            "The historian viewer requires the VOLTTRON web service to be running."
        )
    return web_address.rstrip("/")


async def _access_token(instance: dict, client: httpx.AsyncClient) -> str:
    username = instance.get("web_admin_user", "")
    password = instance.get("web_admin_pass", "")
    if not username or not password:
        raise HistorianViewerError(
            "No web admin credentials are configured for this instance."
        )

    response = await client.post(
        f"{_base_url(instance)}/authenticate",
        json={"username": username, "password": password},
    )
    if response.status_code >= 400:
        raise HistorianViewerError(
            f"Authentication failed: HTTP {response.status_code} {response.text}"
        )

    token = response.json().get("access_token")
    if not token:
        raise HistorianViewerError(
            "Authentication response did not include an access token."
        )
    return token


def _raise_for_api_error(response: httpx.Response, action: str) -> None:
    if response.status_code < 400:
        return
    try:
        payload = response.json()
        detail = payload.get("error") or payload.get("Error") or payload
    except Exception:
        detail = response.text
    raise HistorianViewerError(f"{action} failed: HTTP {response.status_code} {detail}")


def _historians_url(instance: dict) -> str:
    platform = quote(instance.get("name", ""), safe="")
    return f"{_base_url(instance)}/vui/platforms/{platform}/historians"


def _topics_url(instance: dict, historian: str, topic: str = "") -> str:
    """Build the URL for a historian topics request.

    topic may be empty (list all topics), or a full/partial topic path like
    'Campus/Building/Device/Point'.  Each segment is URL-encoded but '/' is
    preserved so the path structure is intact.
    """
    platform = quote(instance.get("name", ""), safe="")
    historian_enc = quote(historian, safe="")
    base = f"{_base_url(instance)}/vui/platforms/{platform}/historians/{historian_enc}/topics"
    if topic:
        encoded_topic = quote(topic, safe="/")
        return f"{base}/{encoded_topic}"
    return base


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def list_historians(instance: dict) -> list[str]:
    """Return a sorted list of running historian VIP identities."""
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        token = await _access_token(instance, client)
        response = await client.get(
            _historians_url(instance),
            headers={"Authorization": f"BEARER {token}"},
        )
        _raise_for_api_error(response, "List historians")
        payload = response.json()
        # Response is {"links": {"<vip_identity>": "/vui/.../historians/<id>", ...}}
        if isinstance(payload, dict):
            links = payload.get("links", payload)
            return sorted(k for k in links if k not in ("error", "links"))
        return []


async def list_topics(instance: dict, historian: str) -> list[str]:
    """Return a sorted flat list of all leaf topic strings reported by the historian.

    Uses read-all=true&values=false so the server returns all leaf-topic keys
    in a single request without fetching any data values.
    """
    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        token = await _access_token(instance, client)
        response = await client.get(
            _topics_url(instance, historian),
            headers={"Authorization": f"BEARER {token}"},
            params={
                "read-all": "true",
                "values": "false",
                "routes": "true",
            },
        )
        _raise_for_api_error(response, "List topics")
        payload = response.json()
        if not isinstance(payload, dict):
            return []
        # Skip the "links" wrapper and special keys; the remaining keys are full topics.
        return sorted(
            k for k in payload
            if k not in ("links", "error", "Error")
        )


async def query_topic(
    instance: dict,
    historian: str,
    topic: str,
    start: str | None = None,
    end: str | None = None,
    skip: int = 0,
    count: int = 500,
    order: str = "LAST_TO_FIRST",
) -> dict:
    """Query time-series data for a single topic via the historian REST API.

    Returns a dict in the grid contract expected by the viewer:
        {
            "columns": ["timestamp", "value"],
            "rows": [{"timestamp": str, "value": any}, ...],
            "metadata": {"units": ..., "type": ..., "tz": ...},   # may be empty
            "returned_count": int,
        }

    Raises HistorianViewerError when:
    - the topic is not a leaf (links response instead of data)
    - any HTTP or auth error occurs
    """
    params: dict[str, str | int] = {
        "skip": skip,
        "count": count,
        "order": order,
        "values": "true",
        "routes": "false",
    }
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        token = await _access_token(instance, client)
        response = await client.get(
            _topics_url(instance, historian, topic),
            headers={"Authorization": f"BEARER {token}"},
            params=params,
        )
        _raise_for_api_error(response, f"Query topic '{topic}'")
        payload = response.json()

    if not isinstance(payload, dict):
        raise HistorianViewerError(
            f"Unexpected response format from historian (expected dict, got {type(payload).__name__})."
        )

    # A "links" key at the top level means the topic is partial (not a leaf point).
    if "links" in payload:
        raise HistorianViewerError(
            f"'{topic}' is not a leaf point — select a specific point from the topic list."
        )

    # Flatten the response into rows.
    # Single-topic response: {"<topic>": {"value": [[ts, val], ...], "metadata": {...}}}
    rows: list[dict] = []
    metadata: dict = {}

    for _topic_key, topic_data in payload.items():
        if not isinstance(topic_data, dict):
            continue
        if not metadata and topic_data.get("metadata"):
            metadata = topic_data["metadata"]
        for entry in topic_data.get("value") or []:
            if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                rows.append({"timestamp": str(entry[0]), "value": entry[1]})

    return {
        "columns": ["timestamp", "value"],
        "rows": rows,
        "metadata": metadata,
        "returned_count": len(rows),
    }
