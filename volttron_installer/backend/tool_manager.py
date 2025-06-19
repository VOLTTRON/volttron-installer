# tools_manager.py
import subprocess
import threading
import sys
import time
import importlib.util
from loguru import logger

class ToolManager:
    """Manages external tool applications that are installed via pip."""
    
    _tool_processes = {}
    
    @classmethod
    def is_package_installed(cls, package_name: str) -> bool:
        """Check if a Python package is installed."""
        return importlib.util.find_spec(package_name) is not None
    
    @classmethod
    def start_tool_service(cls, module_path: str, port: int = 8001, use_poetry: bool = False):
        """
        Start a tool service using the module path directly.
        
        Args:
            module_path: The module path to the FastAPI app (e.g., "bacnet_scan_tool.main:app")
            port: The port to run the tool on
            use_poetry: Whether to run the tool using Poetry
        """
        # Extract package name from module path
        package_name = module_path.split('.')[0]
        
        # Check if the package is installed
        if not cls.is_package_installed(package_name):
            logger.error(f"Error: Package '{package_name}' is not installed.")
            logger.error(f"Please install it using: pip install -e /path/to/{package_name}")
            return False
        
        def run_service():
            try:
                command = []
                
                if use_poetry:
                    # Use Poetry to run the tool
                    command = ["poetry", "run", "uvicorn"]
                else:
                    # Use the current Python interpreter
                    command = [sys.executable, "-m", "uvicorn"]
                
                # Add the module path and parameters
                command.extend([
                    module_path, 
                    "--host", "0.0.0.0", 
                    "--port", str(port)
                ])
                
                logger.debug(f"Starting service: {' '.join(command)}")
                
                # Start the tool in a subprocess
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Store the process
                cls._tool_processes[module_path] = process
                
                # Print output for debugging
                def log_output():
                    for line in process.stdout:
                        logger.debug(f"[{module_path}] {line.strip()}")
                    for line in process.stderr:
                        logger.debug(f"[{module_path} ERROR] {line.strip()}")
                
                # Start output logging thread
                output_thread = threading.Thread(target=log_output, daemon=True)
                output_thread.start()
                
                logger.debug(f"Started tool service '{module_path}' on port {port}")
                return process
                
            except Exception as e:
                logger.error(f"Error starting tool service '{module_path}': {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # Start the service in a separate thread
        thread = threading.Thread(target=run_service, daemon=True)
        thread.start()
        
        # Give the service time to start
        time.sleep(2)
        return True
    
    @classmethod
    def stop_all_tools(cls):
        """Stop all running tool services."""
        for name, process in cls._tool_processes.items():
            try:
                process.terminate()
                print(f"Stopped tool service '{name}'")
            except:
                pass
        cls._tool_processes.clear()