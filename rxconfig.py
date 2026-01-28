import reflex as rx
from dotenv import load_dotenv
from pathlib import Path
import os

if Path("dev.env").exists():
    load_dotenv("dev.env")
elif Path(".env").exists():
    load_dotenv()
else:
    raise FileNotFoundError("No .env nore dev.env file found")

config = rx.Config(
    app_name="volttron_installer",
    backend_port=int(os.environ.get("BACKEND_PORT", 8000)),
    frontend_port=int(os.environ.get("FRONTEND_PORT", 3000)),
    api_url = f'{os.environ.get("API_URL", "http://localhost:8000")}'
)