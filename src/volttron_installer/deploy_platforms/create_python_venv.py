import asyncio
import os

async def create_venv(venv_path: str):
    """
    Creates a Python virtual environment at the specified path.
    """
    expanded_path = os.path.expanduser(venv_path)
    
    if not os.path.exists(expanded_path):
        process = await asyncio.create_subprocess_exec(
            'python3', '-m', 'venv', expanded_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise Exception(f"Failed to create virtual environment: {stderr.decode()}")
            
    return expanded_path
