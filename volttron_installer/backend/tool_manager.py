# Modified tools_manager.py
import os
import subprocess
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
TOOLS_DIR = ROOT_DIR / "tools"

class ToolManager:
    _tool_processes = {}
    
    @classmethod
    def start_tool_service(cls, tool_name: str, module_path: str = None, port: int = 8001):
        tool_path = TOOLS_DIR / tool_name
        
        if not tool_path.exists():
            print(f"Tool '{tool_name}' not found at {tool_path}")
            return False
        
        # Use the correct module path for bacnet-scan-tool
        if tool_name == "bacnet-scan-tool" and module_path is None:
            module_path = "bacnet_scan_tool.main:app"
            
        def run_service():
            try:
                env = os.environ.copy()
                
                # First check if Poetry is installed
                try:
                    subprocess.run(["poetry", "--version"], check=True, stdout=subprocess.PIPE)
                except (subprocess.SubprocessError, FileNotFoundError):
                    print("Poetry not found. Please install Poetry to run this tool.")
                    return
                
                print(f"Starting {tool_name} with module path: {module_path}")
                
                # Run the tool using Poetry
                process = subprocess.Popen(
                    ["poetry", "run", "uvicorn", module_path, "--host", "0.0.0.0", "--port", str(port)],
                    cwd=str(tool_path),
                    env=env
                )
                cls._tool_processes[tool_name] = process
                print(f"Started tool '{tool_name}' on port {port} using Poetry")
                process.wait()
            except Exception as e:
                print(f"Error starting tool '{tool_name}': {str(e)}")
            
        thread = threading.Thread(target=run_service, daemon=True)
        thread.start()
        time.sleep(2)  # Give the service time to start
        return True