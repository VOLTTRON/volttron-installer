import asyncio
import json
import os
import shlex
import sys
import subprocess
from volttron_installer import ssh_remote

async def execute_python_code(instance: dict, code: str, python_executable: str | None = None) -> str:
    """
    Executes a block of Python code on the target instance (local or remote)
    and returns the stdout.

    Args:
        instance: Instance dict from db.get_instances().
        code: Python source to execute.
        python_executable: Optional path to the python interpreter to use.
            For local instances this is passed directly to subprocess; for remote
            instances it replaces the bare 'python3' in the remote command.
            Defaults to sys.executable (local) / 'python3' (remote).
    """
    is_local = instance.get("is_local", True)
    if is_local:
        # Run locally in a subprocess to avoid blocking or crashing the main process
        interpreter = python_executable or sys.executable
        cmd = [interpreter, "-c", code]
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
        interpreter = python_executable or "python3"
        remote_cmd = f"{interpreter} -c {shlex.quote(code)}"
        try:
            stdout, stderr = await ssh_remote.run(instance, remote_cmd)
            return stdout
        except Exception as e:
            raise RuntimeError(f"Remote python execution failed: {e}")