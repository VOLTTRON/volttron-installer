import httpx
from typing import Any, Optional


def get_request(url: str, params: Optional[dict[str, Any]] = None) -> httpx.Response:
    """Send a GET request to the specified URL with optional parameters."""
    response = httpx.get(url, params=params)
    return response

def post_request(url: str, data: Optional[dict[str, Any]] = None) -> httpx.Response:
    """Send a POST request to the specified URL with optional JSON data."""
    response = httpx.post(url, json=data)
    return response

def put_request(url: str, data: Optional[dict[str, Any]] = None) -> httpx.Response:
    """Send a PUT request to the specified URL with optional JSON data."""
    response = httpx.put(url, json=data)
    return response

def delete_request(url: str, params: Optional[dict[str, Any]] = None) -> httpx.Response:
    """Send a DELETE request to the specified URL with optional parameters."""
    response = httpx.delete(url, params=params)
    return response
