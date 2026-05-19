import os
import asyncio
import shlex

from src import ssh_remote

async def start_platform_command(venv_path: str, volttron_home: str, instance: dict | None = None):
    """
    Starts the VOLTTRON platform by executing it in the background via shell,
    exporting the required VOLTTRON_HOME environment variable and using the venv executable.
    """
    if ssh_remote.is_remote_instance(instance):
        expanded_venv = await ssh_remote.expand_path(instance, venv_path)
        expanded_home = await ssh_remote.expand_path(instance, volttron_home)
        volttron_exec = f"{expanded_venv}/bin/volttron"
        log_file = f"{expanded_home}/volttron.log"
        if not await ssh_remote.path_exists(instance, volttron_exec):
            raise Exception(f"VOLTTRON executable not found at {volttron_exec}. Was it installed correctly?")

        quoted_log = shlex.quote(log_file)
        log_start_stdout, _ = await ssh_remote.run(
            instance,
            f"test -f {quoted_log} && wc -c < {quoted_log} || printf 0",
            timeout=30,
        )
        try:
            log_start_size = int(log_start_stdout.strip() or "0")
        except ValueError:
            log_start_size = 0

        cmd = (
            f"export VOLTTRON_HOME={shlex.quote(expanded_home)} && "
            f"source {shlex.quote(f'{expanded_venv}/bin/activate')} && "
            f"volttron -vv -l {quoted_log} >/dev/null 2>&1 &"
        )
        await ssh_remote.run(instance, cmd, timeout=30)

        for _ in range(20):
            await asyncio.sleep(1)
            if await ssh_remote.path_exists(instance, log_file):
                await asyncio.sleep(4)
                stdout, _ = await ssh_remote.run(
                    instance,
                    f"tail -c +{log_start_size + 1} {quoted_log} || true",
                    timeout=30,
                )
                if "PLATFORM HAS SHUTDOWN" in stdout or "Traceback (most recent call last)" in stdout:
                    raise Exception("VOLTTRON crashed during initialization.")
                return True

        raise Exception("VOLTTRON started but took too long to initialize (log file not found).")

    expanded_venv = os.path.expanduser(venv_path)
    expanded_home = os.path.expanduser(volttron_home)
    
    # Ensure the home directory exists
    os.makedirs(expanded_home, exist_ok=True)
    
    volttron_exec = os.path.join(expanded_venv, 'bin', 'volttron')
    log_file = os.path.join(expanded_home, 'volttron.log')
    log_start_size = os.path.getsize(log_file) if os.path.exists(log_file) else 0
    
    if not os.path.exists(volttron_exec):
        raise Exception(f"VOLTTRON executable not found at {volttron_exec}. Was it installed correctly?")
    
    # Start command in background, ensuring we source the venv to fix PATH for subprocesses (like poetry)
    cmd = f"export VOLTTRON_HOME={expanded_home} && source {expanded_venv}/bin/activate && volttron -vv -l {log_file} &>/dev/null &"
    
    await asyncio.create_subprocess_shell(cmd, executable='/bin/bash')
    
    # Wait for VOLTTRON to fully start up by checking if the log file has been populated
    for _ in range(20):
        await asyncio.sleep(1)
        if os.path.exists(log_file):
            # Once the log file exists, give the platform a few more seconds to fully initialize its inner workings
            await asyncio.sleep(4)
            
            # Check the log file for an immediate crash
            try:
                with open(log_file, 'r') as f:
                    f.seek(log_start_size)
                    content = f.read()
                    # Only inspect lines written by this start attempt. Old shutdowns
                    # or tracebacks in volttron.log should not make a good boot fail.
                    if "PLATFORM HAS SHUTDOWN" in content or "Traceback (most recent call last)" in content:
                        raise Exception("VOLTTRON crashed during initialization.")
            except Exception as e:
                if "crashed" in str(e):
                    raise e
            
            return True
            
    raise Exception("VOLTTRON started but took too long to initialize (log file not found).")
