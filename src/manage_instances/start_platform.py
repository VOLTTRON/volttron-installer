import os
import asyncio

async def start_platform_command(venv_path: str, volttron_home: str):
    """
    Starts the VOLTTRON platform by executing it in the background via shell,
    exporting the required VOLTTRON_HOME environment variable and using the venv executable.
    """
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
