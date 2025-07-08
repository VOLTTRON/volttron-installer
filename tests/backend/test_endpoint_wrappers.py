import pytest
import httpx
import asyncio
from unittest.mock import AsyncMock, patch

import sys
import os
# Import the functions to test - adjust the import path as needed
from volttron_installer.thin_endpoint_wrappers import (
    get_request, post_request, put_request, delete_request, 
    ApiError, API_BASE_URL, DEFAULT_TIMEOUT
)

@pytest.fixture
def mock_httpx_client():
    """Fixture to mock httpx.AsyncClient."""
    with patch('httpx.AsyncClient') as mock_client:
        # Create a mock for the client instance
        client_instance = AsyncMock()
        # Configure the mock to return itself for context manager
        mock_client.return_value.__aenter__.return_value = client_instance
        yield client_instance

@pytest.mark.asyncio
async def test_get_request_success(mock_httpx_client):
    """Test successful GET request."""
    # Setup mock response
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test_data"}
    mock_httpx_client.get.return_value = mock_response
    
    # Call the function
    test_url = f"{API_BASE_URL}/test-endpoint"
    response = await get_request(test_url, params={"param": "value"})
    
    # Assertions
    mock_httpx_client.get.assert_called_once_with(test_url, params={"param": "value"})
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response

@pytest.mark.asyncio
async def test_get_request_timeout_error(mock_httpx_client):
    """Test GET request with timeout error."""
    # Setup timeout exception
    mock_httpx_client.get.side_effect = httpx.TimeoutException("Timeout")
    
    # Call and assert
    test_url = f"{API_BASE_URL}/test-endpoint"
    with pytest.raises(ApiError) as exc_info:
        await get_request(test_url)
    
    assert exc_info.value.status_code == 408
    assert f"Request timed out connecting to {test_url}" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_request_http_error(mock_httpx_client):
    """Test GET request with HTTP error."""
    # Setup HTTP error
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    error = httpx.HTTPStatusError("Not Found", request=None, response=mock_response)
    mock_httpx_client.get.return_value = mock_response
    mock_response.raise_for_status.side_effect = error
    
    # Call and assert
    test_url = f"{API_BASE_URL}/test-endpoint"
    with pytest.raises(ApiError) as exc_info:
        await get_request(test_url)
    
    assert exc_info.value.status_code == 404
    assert "Not Found" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_request_generic_error(mock_httpx_client):
    """Test GET request with generic error."""
    # Setup generic exception
    mock_httpx_client.get.side_effect = Exception("Unknown error")
    
    # Call and assert
    test_url = f"{API_BASE_URL}/test-endpoint"
    with pytest.raises(ApiError) as exc_info:
        await get_request(test_url)
    
    assert exc_info.value.status_code == 500
    assert "Unknown error" in exc_info.value.detail

@pytest.mark.asyncio
async def test_post_request_success(mock_httpx_client):
    """Test successful POST request."""
    # Setup mock response
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "new-resource"}
    mock_httpx_client.post.return_value = mock_response
    
    # Call the function
    test_url = f"{API_BASE_URL}/test-endpoint"
    test_data = {"key": "value"}
    response = await post_request(test_url, data=test_data)
    
    # Assertions
    mock_httpx_client.post.assert_called_once_with(test_url, json=test_data)
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response

@pytest.mark.asyncio
async def test_post_request_error(mock_httpx_client):
    """Test POST request with error."""
    # Setup HTTP error
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    error = httpx.HTTPStatusError("Bad Request", request=None, response=mock_response)
    mock_httpx_client.post.return_value = mock_response
    mock_response.raise_for_status.side_effect = error
    
    # Call and assert
    test_url = f"{API_BASE_URL}/test-endpoint"
    with pytest.raises(ApiError) as exc_info:
        await post_request(test_url, data={"key": "value"})
    
    assert exc_info.value.status_code == 400
    assert "Bad Request" in exc_info.value.detail

@pytest.mark.asyncio
async def test_put_request_success(mock_httpx_client):
    """Test successful PUT request."""
    # Setup mock response
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"updated": True}
    mock_httpx_client.put.return_value = mock_response
    
    # Call the function
    test_url = f"{API_BASE_URL}/test-endpoint/123"
    test_data = {"key": "updated-value"}
    response = await put_request(test_url, data=test_data)
    
    # Assertions
    mock_httpx_client.put.assert_called_once_with(test_url, json=test_data)
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response

@pytest.mark.asyncio
async def test_put_request_error(mock_httpx_client):
    """Test PUT request with error."""
    # Setup HTTP error
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    error = httpx.HTTPStatusError("Forbidden", request=None, response=mock_response)
    mock_httpx_client.put.return_value = mock_response
    mock_response.raise_for_status.side_effect = error
    
    # Call and assert
    test_url = f"{API_BASE_URL}/test-endpoint/123"
    with pytest.raises(ApiError) as exc_info:
        await put_request(test_url, data={"key": "value"})
    
    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail

@pytest.mark.asyncio
async def test_delete_request_success(mock_httpx_client):
    """Test successful DELETE request."""
    # Setup mock response
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_httpx_client.delete.return_value = mock_response
    
    # Call the function
    test_url = f"{API_BASE_URL}/test-endpoint/123"
    response = await delete_request(test_url)
    
    # Assertions
    mock_httpx_client.delete.assert_called_once_with(test_url, params=None)
    mock_response.raise_for_status.assert_called_once()
    assert response == mock_response

@pytest.mark.asyncio
async def test_delete_request_error(mock_httpx_client):
    """Test DELETE request with error."""
    # Setup HTTP error
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    error = httpx.HTTPStatusError("Not Found", request=None, response=mock_response)
    mock_httpx_client.delete.return_value = mock_response
    mock_response.raise_for_status.side_effect = error
    
    # Call and assert
    test_url = f"{API_BASE_URL}/test-endpoint/123"
    with pytest.raises(ApiError) as exc_info:
        await delete_request(test_url)
    
    assert exc_info.value.status_code == 404
    assert "Not Found" in exc_info.value.detail

@pytest.mark.asyncio
async def test_custom_timeout(mock_httpx_client):
    """Test making a request with custom timeout."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_httpx_client.get.return_value = mock_response
    
    test_url = f"{API_BASE_URL}/test-endpoint"
    custom_timeout = 10.0
    
    # Use patch to verify the AsyncClient was created with correct timeout
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client_instance
        mock_client_instance.get.return_value = mock_response
        
        await get_request(test_url, timeout=custom_timeout)
        
        # Verify the client was created with the custom timeout
        mock_client_class.assert_called_once()
        assert mock_client_class.call_args[1]['timeout'] == custom_timeout