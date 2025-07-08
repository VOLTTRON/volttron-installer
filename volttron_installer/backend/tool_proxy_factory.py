from typing import Literal
import httpx


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error ({status_code}): {detail}")


class ToolProxyFactory:
    
    @staticmethod
    async def request(
            url: str, 
            method: Literal["PUT", "POST", "GET", "DELETE", "OPTIONS", "PATCH"], 
            timeout=30.0,
            **kwargs
        ):
        """
        Sends an HTTP request to the specified URL using the given method and returns the response.

        Args:
            url (str): The full URL to which the request will be sent.
            method (Literal): The HTTP method to use (e.g., "GET", "POST", etc.).
            timeout (float, optional): Timeout for the request in seconds. Defaults to 30.0.
            **kwargs: Additional arguments to pass to httpx.AsyncClient.request (e.g., headers, json, params).

        Returns:
            httpx.Response: The HTTP response object from the proxied request.

        Raises:
            ApiError: If the request times out, returns a non-2xx status, or another error occurs.
        """
    
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url, 
                    **kwargs
                )
                response.raise_for_status()
                return response
            except httpx.TimeoutException:
                raise ApiError(408, f"Request timed out connecting to {url}")
            except httpx.HTTPStatusError as e:
                raise ApiError(e.response.status_code, e.response.text)
            except Exception as e:
                raise ApiError(500, str(e))