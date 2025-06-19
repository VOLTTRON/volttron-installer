# Modified tools_manager.py
import os
import subprocess
import threading
import time
import importlib
import sys
from pathlib import Path
from loguru import logger

class ToolManager:
    _tool_processes = {}
    
    @classmethod
    def is_package_installed(cls, package_name: str) -> bool:
        """Check if a Python package is installed."""
        try:
            importlib.import_module(package_name)
            return True
        except ImportError:
            return False

    @classmethod
    def start_tool_service(cls, module_path: str, port: int = 8001, environment: str = None):
        """
        Start a tool service using the module path directly.
        
        Args:
            module_path: The module path to the FastAPI app (e.g., "bacnet_scan_tool.main:app")
            port: The port to run the tool on
            environment: Optional environment to use ('poetry' or None for system Python)
        """
        # Extract package name from module path
        package_name = module_path.split('.')[0] if '.' in module_path else module_path.split(':')[0]
        
        # Check if the package is installed
        if not cls.is_package_installed(package_name):
            logger.debug(f"Package '{package_name}' is not installed. Please install it using pip.")
            return False
        
        def run_service():
            try:
                env = os.environ.copy()
                command = []
                
                if environment == 'poetry':
                    # Check if Poetry is installed
                    try:
                        subprocess.run(["poetry", "--version"], check=True, stdout=subprocess.PIPE)
                    except (subprocess.SubprocessError, FileNotFoundError):
                        logger.debug("Poetry not found. Please install Poetry to run this tool.")
                        return
                    command = ["poetry", "run", "uvicorn"]
                else:
                    # Use system Python
                    command = [sys.executable, "-m", "uvicorn"]
                
                # Add the module path and other parameters
                command.extend([
                    module_path, 
                    "--host", "0.0.0.0", 
                    "--port", str(port)
                ])
                
                logger.debug(f"Starting tool with module path: {module_path}")
                logger.debug(f"Running command: {' '.join(command)}")
                
                # Start the process
                process = subprocess.Popen(
                    command,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Print output in real-time
                def print_output():
                    while True:
                        stdout_line = process.stdout.readline()
                        stderr_line = process.stderr.readline()
                        if stdout_line:
                            logger.debug(f"[Tool stdout] {stdout_line.strip()}")
                        if stderr_line:
                            logger.debug(f"[Tool stderr] {stderr_line.strip()}")
                        if not stdout_line and not stderr_line and process.poll() is not None:
                            break
                
                output_thread = threading.Thread(target=print_output, daemon=True)
                output_thread.start()
                
                # Store the process
                cls._tool_processes[module_path] = process
                logger.debug(f"Started tool '{module_path}' on port {port}")
                process.wait()
                
            except Exception as e:
                logger.debug(f"Error starting tool '{module_path}': {str(e)}")
                import traceback
                traceback.print_exc()
            
        thread = threading.Thread(target=run_service, daemon=True)
        thread.start()
        time.sleep(2)  # Give the service time to start
        return True
    
    @classmethod
    def stop_all_tools(cls):
        """Stop all running tool services."""
        for name, process in cls._tool_processes.items():
            try:
                process.terminate()
                logger.debug(f"Stopped tool service '{name}'")
            except:
                pass
        cls._tool_processes.clear()