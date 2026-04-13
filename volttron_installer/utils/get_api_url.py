import os

def get_api_url(url_path: str) -> str:
    api_url = os.environ.get("API_URL", "")
    # python-dotenv doesn't interpolate ${VAR} references — detect and resolve
    if "${" in api_url:
        base_url = os.environ.get("BASE_URL", "http://localhost")
        backend_port = os.environ.get("BACKEND_PORT", "8000")
        api_url = f"{base_url}:{backend_port}"
    if not api_url:
        api_url = f"http://localhost:{os.environ.get('BACKEND_PORT', '8000')}"
    return f"{api_url}{url_path}"