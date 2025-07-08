import importlib.util
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from loguru import logger

class ToolManager:
    """Manages external tool applications with on-demand initialization and inactivity monitoring."""
    
    _tool_processes: Dict[str, subprocess.Popen] = {}
    _tool_ports: Dict[str, int] = {}
    _tool_last_access: Dict[str, float] = {}
    _next_available_port = 8001
    _inactivity_monitor_running = False
    _inactivity_timeout_minutes = 30  # Default timeout
    
    @classmethod
    def is_tool_running(cls, tool_name: str) -> bool:
        """Check if a specific tool is currently running."""
        normalized_name = cls._normalize_tool_name(tool_name)
        if normalized_name not in cls._tool_processes:
            return False
            
        process = cls._tool_processes[normalized_name]
        return process.poll() is None  # None means process is still running
    
    @classmethod
    def get_tool_port(cls, tool_name: str) -> Optional[int]:
        """Get the port a tool is running on."""
        normalized_name = cls._normalize_tool_name(tool_name)
        return cls._tool_ports.get(normalized_name)
    
    @classmethod
    def record_tool_access(cls, tool_name: str) -> None:
        """Record that a tool was accessed."""
        normalized_name = cls._normalize_tool_name(tool_name)
        if normalized_name in cls._tool_processes:
            cls._tool_last_access[normalized_name] = time.time()
            logger.debug(f"Tool access recorded: {tool_name} at {datetime.now().strftime('%H:%M:%S')}")

    @classmethod
    def _normalize_tool_name(cls, name):
        """Normalize tool names to avoid case/format mismatches"""
        return str(name).lower().replace(" ", "_")

    @classmethod
    def start_tool_service(cls, 
                        tool_name: str,
                        module_path: str, 
                        port: int = None, 
                        use_poetry: bool = False,
                        poetry_project_path: str = None) -> dict:
        """
        Start a tool service on-demand.
        
        Returns:
            dict: Status information including success, port, and any error message
        """
        # Normalize the tool name for consistent lookups
        normalized_name = cls._normalize_tool_name(tool_name)
        
        # Start inactivity monitor if not already running
        if not cls._inactivity_monitor_running:
            cls._start_inactivity_monitor()
        
        # If already running, record access and return the current port
        if cls.is_tool_running(normalized_name):
            cls.record_tool_access(normalized_name)
            return {
                "success": True,
                "port": cls._tool_ports[normalized_name],
                "message": f"Tool '{tool_name}' is already running"
            }
        
        # Assign a port if not specified
        if port is None:
            port = cls._next_available_port
            cls._next_available_port += 1
        
        # Extract package name from module path
        package_name = module_path.split('.')[0]
        
        # Check if the package is installed
        if not importlib.util.find_spec(package_name):
            return {
                "success": False,
                "message": f"Package '{package_name}' is not installed"
            }
        
        # Find the package location if using Poetry
        if use_poetry:
            if not poetry_project_path:
                # Try to find the repository location
                poetry_project_path = cls._find_repo_directory(package_name)
            
            if not poetry_project_path or not os.path.exists(poetry_project_path):
                return {
                    "success": False, 
                    "message": f"Could not find Poetry project path for {package_name}"
                }
        
        # Start the tool in a separate thread
        def run_service():
            try:
                command = []
                env = os.environ.copy()
                
                if use_poetry:
                    # Check if Poetry is installed
                    try:
                        subprocess.run(["poetry", "--version"], check=True, stdout=subprocess.PIPE)
                    except (subprocess.SubprocessError, FileNotFoundError):
                        logger.debug(f"Poetry not found. Please install Poetry to run {tool_name}.")
                        return
                    
                    # Use Poetry to run the tool
                    command = ["poetry", "run", "uvicorn"]
                    cwd = poetry_project_path
                else:
                    # Use the current Python interpreter
                    command = [sys.executable, "-m", "uvicorn"]
                    cwd = None
                
                # Add the module path and parameters
                command.extend([
                    module_path, 
                    "--host", "0.0.0.0", 
                    "--port", str(port)
                ])
                
                logger.debug(f"Starting {tool_name} with command: {' '.join(command)}")
                
                # Start the tool in a subprocess
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=cwd,
                    env=env,
                    bufsize=1
                )
                
                # Store the process and port using normalized name
                cls._tool_processes[normalized_name] = process
                cls._tool_ports[normalized_name] = port
                
                # Record initial access time
                cls.record_tool_access(normalized_name)
                
                # Print output for debugging
                def log_output(pipe, prefix):
                    for line in iter(pipe.readline, ''):
                        if not line:
                            break
                        logger.debug(f"[{tool_name}{prefix}] {line.strip()}")
                
                # Start output logging thread
                stdout_thread = threading.Thread(
                    target=log_output, 
                    args=(process.stdout, ""), 
                    daemon=True
                )
                stderr_thread = threading.Thread(
                    target=log_output, 
                    args=(process.stderr, " ERROR"),
                    daemon=True
                )
                stdout_thread.start()
                stderr_thread.start()
                # Monitor process and clean up when it exits
                process.wait()
                
                stdout_thread.join(timeout=2)
                stderr_thread.join(timeout=2)
                
                # Process has exited, clean up
                if normalized_name in cls._tool_processes and cls._tool_processes[normalized_name] == process:
                    del cls._tool_processes[normalized_name]
                    if normalized_name in cls._tool_ports:
                        del cls._tool_ports[normalized_name]
                    if normalized_name in cls._tool_last_access:
                        del cls._tool_last_access[normalized_name]
                    
                    logger.debug(f"Tool service '{tool_name}' has stopped")
                    
            except Exception as e:
                logger.debug(f"Error running tool service '{tool_name}': {e}")
                import traceback
                traceback.print_exc()
        
        # Start the service thread
        thread = threading.Thread(target=run_service, daemon=True)
        thread.start()
        
        # Give the service a moment to start
        time.sleep(2)
        
        # Check if the process is running
        if cls.is_tool_running(normalized_name):
            # Debug info to help troubleshoot
            logger.debug(f"Tool processes dictionary keys: {list(cls._tool_processes.keys())}")
            logger.debug(f"Is tool '{normalized_name}' running? {cls.is_tool_running(normalized_name)}")
            
            return {
                "success": True,
                "port": port,
                "message": f"Started tool '{tool_name}' on port {port}"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to start tool '{tool_name}'"
            }
        
    @classmethod
    def stop_tool_service(cls, tool_name: str) -> dict:
        """
        Stop a specific tool service.
        
        Returns:
            dict: Status information including success and any message
        """
        from loguru import logger
        normalized_name = cls._normalize_tool_name(tool_name)

        if normalized_name not in cls._tool_processes:
            return {"success": False, "message": f"Tool '{normalized_name}' is not running"}
        
        try:
            process = cls._tool_processes[normalized_name]
            process.terminate()
            
            # Wait a moment for graceful shutdown
            for _ in range(5):
                if process.poll() is not None:  # Process has exited
                    break
                time.sleep(0.5)
            
            # Force kill if still running
            if process.poll() is None:
                process.kill()
            
            # Log current state before cleanup
            logger.debug(f"Before cleanup: _tool_processes: {list(cls._tool_processes.keys())}")
            
            # Clean up
            # Usually this check wont go through because when we kill the process, the function run_service() detects,
            # that we ended the process and will clean up there.
            if normalized_name in cls._tool_processes:
                # If not, we'll do it here
                logger.debug(f"Cleaning up tool in stop_tool_service: {normalized_name}")
                del cls._tool_processes[normalized_name]
                if normalized_name in cls._tool_ports:
                    del cls._tool_ports[normalized_name]
                if normalized_name in cls._tool_last_access:
                    del cls._tool_last_access[normalized_name]
                
            logger.debug(f"After cleanup: _tool_processes: {list(cls._tool_processes.keys())}")
            return {"success": True, "message": f"Stopped tool '{normalized_name}'"}
        except Exception as e:
            logger.exception(f"Exception when stopping tool '{normalized_name}'")
            return {"success": False, "message": f"Error stopping tool '{normalized_name}': {str(e)}"}
    
    @classmethod
    def stop_all_tools(cls):
        """Stop all running tool services."""
        tool_names = list(cls._tool_processes.keys())
        for name in tool_names:
            cls.stop_tool_service(name)
    
    @classmethod
    def set_inactivity_timeout(cls, minutes: int) -> None:
        """
        Set the inactivity timeout for automatic tool shutdown.
        
        Args:
            minutes: Number of minutes after which inactive tools should be shut down
        """
        if minutes < 1:
            raise ValueError("Inactivity timeout must be at least 1 minute")
            
        cls._inactivity_timeout_minutes = minutes
        logger.debug(f"Tool inactivity timeout set to {minutes} minutes")
    
    @classmethod
    def _start_inactivity_monitor(cls) -> None:
        """Start monitoring tool inactivity."""
        if cls._inactivity_monitor_running:
            return
            
        def monitor_inactivity():
            cls._inactivity_monitor_running = True
            logger.debug(f"Tool inactivity monitor started (timeout: {cls._inactivity_timeout_minutes} minutes)")
            
            while True:
                try:
                    current_time = time.time()
                    timeout_seconds = cls._inactivity_timeout_minutes * 60
                    
                    # Check each running tool
                    for tool_name in list(cls._tool_processes.keys()):
                        if tool_name not in cls._tool_last_access:
                            # No access record, create one
                            cls._tool_last_access[tool_name] = current_time
                            continue
                            
                        last_access = cls._tool_last_access[tool_name]
                        elapsed_seconds = current_time - last_access
                        
                        # If tool has been inactive for longer than the timeout, stop it
                        if elapsed_seconds > timeout_seconds:
                            logger.debug(f"Stopping inactive tool '{tool_name}' (inactive for {elapsed_seconds/60:.1f} minutes)")
                            cls.stop_tool_service(tool_name)
                            
                except Exception as e:
                    logger.debug(f"Error in inactivity monitor: {e}")
                    
                # Check every minute
                time.sleep(60)
        
        # Start monitoring in a separate thread
        thread = threading.Thread(target=monitor_inactivity, daemon=True)
        thread.start()
    
    @classmethod
    def _find_repo_directory(cls, package_name: str) -> Optional[str]:
        """Find the repository directory for an installed package."""
        try:
            spec = importlib.util.find_spec(package_name)
            if not spec or not spec.origin:
                return None
                
            # Get module directory
            module_dir = os.path.dirname(spec.origin)
            
            # Navigate to find pyproject.toml
            current_dir = module_dir
            for _ in range(5):  # Check up to 5 levels up
                if os.path.exists(os.path.join(current_dir, "pyproject.toml")):
                    return current_dir
                parent_dir = os.path.dirname(current_dir)
                if parent_dir == current_dir:  # Reached root
                    break
                current_dir = parent_dir
                
            # If not found, try src pattern
            if "site-packages" in module_dir:
                src_dir = os.path.join(os.path.dirname(module_dir), "src", package_name.replace("_", "-"))
                if os.path.exists(os.path.join(src_dir, "pyproject.toml")):
                    return src_dir
            
            return None
        except Exception as e:
            logger.debug(f"Error finding repo directory: {e}")
            return None