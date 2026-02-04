import reflex as rx
import subprocess
import asyncio
from loguru import logger
from ..backend.models import CreatePlatformRequest, PlatformConfig, AgentDefinition, ConfigStoreEntry
from ..thin_endpoint_wrappers import get_platform_logs, delete_platform_logs, ApiError

# Module-level dict to track tail processes
_tail_processes: dict[str, subprocess.Popen] = {}

from .platform_base import PlatformBaseState

class PlatformLogState(PlatformBaseState):
    # Log viewing
    _platform_logs: str = ""
    _logs_loading: bool = False
    _log_font_size: int = 12  # Font size in pixels
    _log_wrap: bool = True  # Whether to wrap long log lines
    _tailing: bool = False  # Whether we're actively tailing logs

    @rx.var
    def platform_logs(self) -> str:
        return self._platform_logs
    
    @rx.var
    def logs_loading(self) -> bool:
        return self._logs_loading
    
    @rx.var
    def log_font_size(self) -> int:
        return self._log_font_size
    
    @rx.var
    def log_wrap(self) -> bool:
        return self._log_wrap

    @rx.var
    def parsed_log_lines(self) -> list[dict[str, str]]:
        """Parse log lines and determine their log level for coloring."""
        if not self._platform_logs:
            return []

        lines = self._platform_logs.split("\n")
        result = []
        for line in lines:
            level = "default"
            line_upper = line.upper()
            if " DEBUG" in line_upper or "DEBUG:" in line_upper:
                level = "debug"
            elif " INFO" in line_upper or "INFO:" in line_upper:
                level = "info"
            elif " WARNING" in line_upper or "WARNING:" in line_upper or " WARN " in line_upper:
                level = "warning"
            elif " ERROR" in line_upper or "ERROR:" in line_upper:
                level = "error"
            elif " CRITICAL" in line_upper or "CRITICAL:" in line_upper:
                level = "critical"
            result.append({"text": line, "level": level})
        return result

    @rx.var
    def tailing(self) -> bool:
        """Whether we're actively tailing logs"""
        return self._tailing

    @rx.event(background=True)
    async def fetch_platform_logs(self, lines: int = 100):
        """Fetch VOLTTRON platform logs"""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return
            
            self._logs_loading = True
            working_platform: Instance = self.working_platform
            instance_name = working_platform.platform.config.instance_name
            
        yield
        
        try:
            result = await get_platform_logs(instance_name, lines)
            
            async with self:
                self._platform_logs = result.get("logs", "No logs available")
                self._logs_loading = False
                
        except ApiError as e:
            async with self:
                self._platform_logs = f"Error fetching logs: {e.detail}"
                self._logs_loading = False
        except Exception as e:
            async with self:
                self._platform_logs = f"Error: {str(e)}"
                self._logs_loading = False

    @rx.event(background=True)
    async def delete_platform_logs(self):
        """Delete VOLTTRON platform logs"""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return
            
            self._logs_loading = True
            working_platform: Instance = self.working_platform
            instance_name = working_platform.platform.config.instance_name
            
        yield
        
        try:
            result = await delete_platform_logs(instance_name)
            
            async with self:
                self._platform_logs = "Log file deleted. Click 'Refresh Logs' to verify."
                self._logs_loading = False
                
            yield rx.toast.success("Log file deleted successfully!")
                
        except ApiError as e:
            async with self:
                self._platform_logs = f"Error deleting logs: {e.detail}"
                self._logs_loading = False
            yield rx.toast.error(f"Failed to delete logs: {e.detail}")
        except Exception as e:
            async with self:
                self._platform_logs = f"Error: {str(e)}"
                self._logs_loading = False
            yield rx.toast.error(f"Error deleting logs: {str(e)}")
    
    def increase_log_font_size(self):
        """Increase log font size"""
        self._log_font_size = min(32, self._log_font_size + 2)
    
    def decrease_log_font_size(self):
        """Decrease log font size"""
        self._log_font_size = max(8, self._log_font_size - 2)
    
    def toggle_log_wrap(self):
        """Toggle log line wrapping"""
        self._log_wrap = not self._log_wrap

    @rx.event(background=True)
    async def start_tailing(self):
        """Start tailing logs with tail -f over SSH"""
        global _tail_processes

        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return

            if self._tailing:
                return  # Already tailing

            working_platform: Instance = self.working_platform
            platform_id = working_platform.platform.config.instance_name
            host = working_platform.host

            # Get connection details
            ansible_user = host.ansible_user
            ansible_host = host.ansible_host
            ansible_port = str(host.ansible_port)
            volttron_home = host.volttron_home if host.volttron_home else "~/.volttron"

            self._tailing = True
            self._platform_logs = ""  # Clear existing logs

        yield

        try:
            # Build SSH command for tail -f
            ssh_cmd = [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "BatchMode=yes",
                "-p", ansible_port,
                f"{ansible_user}@{ansible_host}",
                f"tail -f {volttron_home}/volttron.log 2>/dev/null || echo 'Log file not found'"
            ]

            logger.debug(f"Starting tail process: {' '.join(ssh_cmd)}")

            # Start the subprocess
            process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )

            _tail_processes[platform_id] = process

            yield rx.toast.info("Started live log streaming...")

            # Read lines in a loop
            log_buffer = []
            while True:
                # Check if we should stop
                async with self:
                    should_continue = self._tailing

                if not should_continue:
                    break

                # Check if process is still running
                if process.poll() is not None:
                    async with self:
                        self._tailing = False
                    yield rx.toast.warning("Log stream ended")
                    break

                # Try to read a line (non-blocking would be better but this works)
                try:
                    # Use select to check if data is available (Unix only)
                    import select
                    ready, _, _ = select.select([process.stdout], [], [], 0.5)

                    if ready:
                        line = process.stdout.readline()
                        if line:
                            log_buffer.append(line.rstrip('\n'))
                            # Update state with new lines (batch updates for performance)
                            if len(log_buffer) >= 1:
                                async with self:
                                    # Append new lines to existing logs
                                    new_content = '\n'.join(log_buffer)
                                    if self._platform_logs:
                                        self._platform_logs = self._platform_logs + '\n' + new_content
                                    else:
                                        self._platform_logs = new_content
                                    # Keep only last 1000 lines to prevent memory issues
                                    lines = self._platform_logs.split('\n')
                                    if len(lines) > 1000:
                                        self._platform_logs = '\n'.join(lines[-1000:])
                                log_buffer = []
                                yield  # Update UI
                    else:
                        # No data available, just yield to allow UI updates
                        await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error reading tail output: {e}")
                    await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error starting tail: {e}")
            async with self:
                self._tailing = False
            yield rx.toast.error(f"Failed to start log streaming: {str(e)}")
        finally:
            # Clean up process
            if platform_id in _tail_processes:
                try:
                    _tail_processes[platform_id].terminate()
                    _tail_processes[platform_id].wait(timeout=2)
                except:
                    try:
                        _tail_processes[platform_id].kill()
                    except:
                        pass
                del _tail_processes[platform_id]

    @rx.event
    def stop_tailing(self):
        """Stop tailing logs"""
        global _tail_processes

        self._tailing = False

        # Get platform ID
        if self.current_uid and self.current_uid in self.platforms:
            working_platform: Instance = self.working_platform
            platform_id = working_platform.platform.config.instance_name

            # Kill the process if it exists
            if platform_id in _tail_processes:
                try:
                    _tail_processes[platform_id].terminate()
                except:
                    pass
                if platform_id in _tail_processes:
                    del _tail_processes[platform_id]
