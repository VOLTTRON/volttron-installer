import httpx
from fastapi import APIRouter, Request, HTTPException
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
from .tool_manager import ToolManager

# Create a router for dynamic proxying
tool_router = APIRouter(prefix="/tool_proxy", tags=["tool proxy"])

@tool_router.api_route("/{tool_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
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
    target_url = f"http://localhost:{port}/{path}"
    
    # Get request details
    headers = {k: v for k, v in request.headers.items() 
              if k.lower() not in ("host", "content-length")}
    content = await request.body()
    
    # Create client
    client = httpx.AsyncClient()
    async def close_client():
        await client.aclose()
        
    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=content,
            params=request.query_params,
            cookies=request.cookies,
        )
        
        return StreamingResponse(
            response.aiter_bytes(),
            status_code=response.status_code,
            headers=dict(response.headers),
            background=BackgroundTask(close_client)
        )
    except Exception as e:
        await client.aclose()
        raise HTTPException(status_code=500, detail=f"Error proxying to tool: {str(e)}")