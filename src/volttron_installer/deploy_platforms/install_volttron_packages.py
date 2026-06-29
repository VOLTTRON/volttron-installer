import asyncio
import os

async def install_packages(venv_path: str, packages: list[str]):
    """
    Installs pip packages into the specified virtual environment.
    """
    expanded_path = os.path.expanduser(venv_path)
    pip_executable = os.path.join(expanded_path, 'bin', 'pip')
    
    if not os.path.exists(pip_executable):
        raise Exception(f"Virtual environment not found at {expanded_path}")
        
    for package in packages:
        pkg_args = package.split(' ')
        args = [pip_executable, 'install'] + pkg_args
        
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Failed to install package '{package}': {stderr.decode()}")
        
    return stdout.decode()
