import httpx
from fastapi import APIRouter, Request
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

# Create a router for the tool
tool_router = APIRouter(tags=["tools"])

@tool_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_to_tool(request: Request, path: str):
    target_url = f"http://localhost:8001/{path}"
    
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
        raise e