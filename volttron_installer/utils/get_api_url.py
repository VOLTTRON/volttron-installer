import os

def get_api_url(url_path: str) -> str:
    return f'{os.environ.get("API_URL")}{url_path}'