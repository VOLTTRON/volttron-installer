import httpx
from fastapi import APIRouter, Request, HTTPException
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
from .tool_manager import ToolManager
from dotenv import load_dotenv
from pathlib import Path
import os

if Path("dev.env").exists():
    load_dotenv("dev.env")
elif Path(".env").exists():
    load_dotenv()
else:
    raise FileNotFoundError("No .env nore dev.env file found")

# Create a router for dynamic proxying
tool_router = APIRouter(prefix="/tool_proxy", tags=["tool proxy"])

@tool_router.get("/{tool_name}/{path:path}")
async def tool_proxy_get(request: Request, tool_name: str, path: str):
    response = await proxy_to_tool(request, tool_name, path)
    return response

@tool_router.post("/{tool_name}/{path:path}")
async def tool_proxy_post(request: Request, tool_name: str, path: str):
    response = await proxy_to_tool(request, tool_name, path)
    return response

@tool_router.put("/{tool_name}/{path:path}")
async def tool_proxy_put(request: Request, tool_name: str, path: str):
    response = await proxy_to_tool(request, tool_name, path)
    return response

@tool_router.delete("/{tool_name}/{path:path}")
async def tool_proxy_delete(request: Request, tool_name: str, path: str):
    response = await proxy_to_tool(request, tool_name, path)
    return response

@tool_router.patch("/{tool_name}/{path:path}")
async def tool_proxy_patch(request: Request, tool_name: str, path: str):
    response = await proxy_to_tool(request, tool_name, path)
    return response

@tool_router.options("/{tool_name}/{path:path}")
async def tool_proxy_options(request: Request, tool_name: str, path: str):
    response = await proxy_to_tool(request, tool_name, path)
    return response

async def proxy_to_tool(request: Request, tool_name: str, path: str):
    """
    Dynamically proxy requests to the appropriate tool.
    
    If the tool isn't running, returns a 503 Service Unavailable.
    """
    # Check if tool is running
    if not ToolManager.is_tool_running(tool_name):
        raise HTTPException(
            status_code=503, 
            detail=f"Tool '{tool_name}' is not currently running. Start it first via /api/tools/start_tool"
        )
    
    # Record tool access
    ToolManager.record_tool_access(tool_name)
    
    # Get the port the tool is running on
    port = ToolManager.get_tool_port(tool_name)
    if not port:
        raise HTTPException(status_code=500, detail="Could not determine tool port")
    
    # Proxy the request to the tool
    target_url = f"{os.environ.get('TOOL_PROXY_URL', 'http://localhost')}:{port}/{path}"
    
    # Get request details - preserve everything
    headers = {k: v for k, v in request.headers.items() 
              if k.lower() not in ("host", "content-length")}
    content = await request.body()
    
    # Create client
    client = httpx.AsyncClient(timeout=300.0)  # 5 minutes
    async def close_client():
        await client.aclose()
        
    try:
        # Forward the request with all original properties
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=content,
            params=request.query_params,
            cookies=request.cookies,
        )
        
        # Return the response exactly as received
        return StreamingResponse(
            response.aiter_bytes(),
            status_code=response.status_code,
            headers=dict(response.headers),
            background=BackgroundTask(close_client)
        )
    except httpx.TimeoutException as e:
        await client.aclose()
        raise HTTPException(
            status_code=504,  # Gateway Timeout is more appropriate for timeouts
            detail=f"The operation timed out. {target_url} method may take longer than the allowed request time."
        )
    except Exception as e:
        import traceback
        from loguru import logger
        logger.debug(f"Error details: {str(e)}")
        logger.debug(f"Target URL: {target_url}")
        logger.debug(f"Request method: {request.method}")
        logger.debug(f"Content: {content}")
        logger.debug(traceback.format_exc())
        await client.aclose()
        raise HTTPException(status_code=500, detail=f"Error proxying to tool: {str(e)}")