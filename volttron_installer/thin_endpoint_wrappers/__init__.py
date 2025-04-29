import httpx, asyncio
from typing import Any, Optional

API_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 5.0  # 5 seconds timeout

class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error ({status_code}): {detail}")

# Async HTTP functions
async def get_request(url: str, params: Optional[dict[str, Any]] = None, 
                      timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Send an async GET request to the specified URL with optional parameters."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise ApiError(408, f"Request timed out connecting to {url}")
        except httpx.HTTPStatusError as e:
            raise ApiError(e.response.status_code, e.response.text)
        except Exception as e:
            raise ApiError(500, str(e))

async def post_request(url: str, data: Optional[dict[str, Any]] = None,
                       timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Send an async POST request to the specified URL with optional JSON data."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise ApiError(408, f"Request timed out connecting to {url}")
        except httpx.HTTPStatusError as e:
            raise ApiError(e.response.status_code, e.response.text)
        except Exception as e:
            raise ApiError(500, str(e))

async def put_request(url: str, data: Optional[dict[str, Any]] = None,
                     timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Send an async PUT request to the specified URL with optional JSON data."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            response = await client.put(url, json=data)
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise ApiError(408, f"Request timed out connecting to {url}")
        except httpx.HTTPStatusError as e:
            raise ApiError(e.response.status_code, e.response.text)
        except Exception as e:
            raise ApiError(500, str(e))

async def delete_request(url: str, params: Optional[dict[str, Any]] = None,
                        timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Send an async DELETE request to the specified URL with optional parameters."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            response = await client.delete(url, params=params)
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            raise ApiError(408, f"Request timed out connecting to {url}")
        except httpx.HTTPStatusError as e:
            raise ApiError(e.response.status_code, e.response.text)
        except Exception as e:
            raise ApiError(500, str(e))