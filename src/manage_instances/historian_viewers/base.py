import asyncio
import json
import os
import shlex
import sys
import subprocess
from src import ssh_remote

async def execute_python_code(instance: dict, code: str) -> str:
    """
    Executes a block of Python code on the target instance (local or remote)
    and returns the stdout.
    """
    is_local = instance.get("is_local", True)
    if is_local:
        # Run locally in a subprocess to avoid blocking or crashing the main process
        cmd = [sys.executable, "-c", code]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(stderr.decode(errors="replace").strip())
            return stdout.decode(errors="replace")
        except Exception as e:
            raise RuntimeError(f"Local python execution failed: {e}")
    else:
        # Run remotely via SSH
        # We wrap the code in python3 -c
        remote_cmd = f"python3 -c {shlex.quote(code)}"
        try:
            stdout, stderr = await ssh_remote.run(instance, remote_cmd)
            return stdout
        except Exception as e:
            raise RuntimeError(f"Remote python execution failed: {e}")