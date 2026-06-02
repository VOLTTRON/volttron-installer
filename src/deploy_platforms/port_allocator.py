import socket
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse, urlunparse

import src.db as db


def _normalize_host(host: str) -> str:
    host = (host or "localhost").strip().lower()
    if host in {"127.0.0.1", "::1", "0.0.0.0", "*"}:
        return "localhost"
    return host


def _is_port_bound(host: str, port: int) -> bool:
    connect_host = "127.0.0.1" if _normalize_host(host) == "localhost" else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((connect_host, port)) == 0


def _ports_recorded_for_host(host: str) -> set[int]:
    normalized_host = _normalize_host(host)
    ports: set[int] = set()
    for instance in db.get_instances():
        instance_host = _normalize_host(instance.get("host", "localhost"))
        if instance_host != normalized_host:
            continue
        bind_address = instance.get("web_bind_address", "")
        if not bind_address:
            continue
        parsed = urlparse(bind_address)
        if parsed.port:
            ports.add(parsed.port)
    return ports


def allocate_web_bind_address(requested_address: str, host: str, can_probe_socket: bool) -> tuple[str, list[str]]:
    """
    Return a web bind address whose port is not already recorded for this host.

    For local deployments we also probe the OS socket table, catching stale
    running platforms that no longer have an instances_data record.
    """
    parsed = urlparse(requested_address)
    scheme = parsed.scheme or "http"
    hostname = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if scheme == "https" else 80)
    recorded_ports = _ports_recorded_for_host(host)
    messages: list[str] = []
    original_port = port

    while port in recorded_ports or (can_probe_socket and _is_port_bound(hostname, port)):
        reasons = []
        if port in recorded_ports:
            reasons.append("already recorded for this host")
        if can_probe_socket and _is_port_bound(hostname, port):
            reasons.append("currently bound")
        messages.append(f"Web port {port} is unavailable ({', '.join(reasons)}); trying {port + 1}.")
        port += 1

    netloc = f"{hostname}:{port}"
    allocated = urlunparse((scheme, netloc, parsed.path or "", "", "", ""))
    if port != original_port:
        messages.append(f"Using web bind address {allocated}.")
    return allocated, messages


async def allocate_remote_web_bind_address(
    requested_address: str,
    host: str,
    is_remote_port_bound: Callable[[str, int], Awaitable[bool]],
) -> tuple[str, list[str]]:
    """
    Return a remote web bind address whose port is not recorded or already
    listening on the target host.
    """
    parsed = urlparse(requested_address)
    scheme = parsed.scheme or "http"
    hostname = parsed.hostname or "0.0.0.0"
    port = parsed.port or (443 if scheme == "https" else 80)
    recorded_ports = _ports_recorded_for_host(host)
    messages: list[str] = []
    original_port = port

    while True:
        remote_bound = await is_remote_port_bound(hostname, port)
        reasons = []
        if port in recorded_ports:
            reasons.append("already recorded for this host")
        if remote_bound:
            reasons.append("currently bound on the remote host")
        if not reasons:
            break
        messages.append(f"Web port {port} is unavailable ({', '.join(reasons)}); trying {port + 1}.")
        port += 1

    netloc = f"{hostname}:{port}"
    allocated = urlunparse((scheme, netloc, parsed.path or "", "", "", ""))
    if port != original_port:
        messages.append(f"Using web bind address {allocated}.")
    return allocated, messages
