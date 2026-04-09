import reflex as rx
import asyncio
from loguru import logger
from datetime import datetime
from ..models import Instance
from ..thin_endpoint_wrappers import get_platform_status, mark_platform_deployed, check_platform_connection, start_platform, stop_platform, ApiError

from .platform_logs import PlatformLogState


START_STOP_TIMEOUT_SECONDS = 30
START_STOP_POLL_INTERVAL_SECONDS = 2

# Module-level lock for status check mutual exclusion.
# This is safe because Reflex serializes state mutations per-session,
# and concurrent status checks for the same platform should be deduplicated.
_status_lock = asyncio.Lock()


class PlatformStatusState(PlatformLogState):
    # Platform status tracking
    _platform_status: dict = {}  # Stores PlatformDeploymentStatus data
    _status_loading: bool = False
    _last_refresh_request: float = 0.0  # Timestamp of last refresh request for debouncing
    _status_error: str = ""
    _last_status_check: str = ""
    _starting_platform: bool = False  # True while starting VOLTTRON
    _stopping_platform: bool = False  # True while stopping VOLTTRON

    # Connection status tracking
    _connection_status: str = "unknown"  # connected, disconnected, checking, unknown
    _connection_method: str = ""  # e.g., "SSH with key authentication"
    _last_connection_check: str = ""
    _connection_error: str = ""

    # Platform status computed vars
    @rx.var
    def platform_status(self) -> dict:
        return self._platform_status

    @rx.var
    def status_loading(self) -> bool:
        # Show loading state if explicitly loading OR if deployed platform hasn't been checked yet
        if self._status_loading:
            return True
        # If platform is deployed but no status check has been done, show as loading
        if self.platform_deployed and not self._last_status_check and not self._platform_status:
            return True
        return False

    @rx.var
    def status_error(self) -> str:
        return self._status_error

    @rx.var
    def platform_state(self) -> str:
        # If platform is deployed but no check has been done, show as checking
        if self.platform_deployed and not self._last_status_check and not self._platform_status:
            return "checking"
        return self._platform_status.get("state", "unknown")

    @rx.var
    def platform_agents(self) -> dict:
        return self._platform_status.get("agents", {})

    @rx.var
    def platform_agents_list(self) -> list[dict]:
        """Convert agents dict to list for easier rendering"""
        agents = self._platform_status.get("agents", {})
        return [{"id": agent_id, **agent_data} for agent_id, agent_data in agents.items()]

    @rx.var
    def last_status_check(self) -> str:
        return self._last_status_check

    @rx.var
    def last_status_check_ago(self) -> str:
        if not self._last_status_check:
            return ""
        try:
            then = datetime.strptime(self._last_status_check, "%Y-%m-%d %H:%M:%S")
            diff = datetime.now() - then
            seconds = int(diff.total_seconds())
            if seconds < 5:
                return "just now"
            if seconds < 60:
                return f"{seconds} seconds ago"
            minutes = seconds // 60
            if minutes == 1:
                return "1 minute ago"
            if minutes < 60:
                return f"{minutes} minutes ago"
            hours = minutes // 60
            if hours == 1:
                return "1 hour ago"
            return f"{hours} hours ago"
        except Exception:
            return ""

    @rx.var
    def starting_platform(self) -> bool:
        return self._starting_platform

    @rx.var
    def stopping_platform(self) -> bool:
        return self._stopping_platform

    # Connection status computed vars
    @rx.var
    def connection_status(self) -> str:
        # If platform is deployed but no connection check has been done, show as checking
        if self.platform_deployed and not self._last_connection_check and self._connection_status == "unknown":
            return "checking"
        return self._connection_status

    @rx.var
    def connection_method(self) -> str:
        return self._connection_method

    @rx.var
    def last_connection_check(self) -> str:
        return self._last_connection_check

    @rx.var
    def connection_error(self) -> str:
        return self._connection_error

    @rx.var
    def connection_tooltip(self) -> str:
        """Generate tooltip text for connection status"""
        if self._connection_method:
            tooltip = self._connection_method
            if self._last_connection_check:
                tooltip += f" (Last: {self._last_connection_check})"
            if self._connection_error:
                tooltip += f" - Error: {self._connection_error}"
            return tooltip
        return "Connection status unknown"

    @rx.event(background=True)
    async def refresh_platform_status_debounced(self):
        """Debounced version - waits 2 seconds before refreshing to batch multiple operations"""
        import time

        async with self:
            self._last_refresh_request = time.time()
            request_time = self._last_refresh_request

        # Wait 2 seconds
        await asyncio.sleep(2)

        async with self:
            # Only refresh if no newer request came in
            if request_time == self._last_refresh_request:
                yield PlatformStatusState.refresh_platform_status

    @rx.event(background=True)
    async def load_platform_status_background(self):
        """Background version for initial page load - shows loading state immediately"""
        # Set loading states immediately so UI shows spinners
        async with self:
            self._status_loading = True
            self._connection_status = "checking"

        # Now run the actual status checks (these will update state when done)
        yield PlatformStatusState.refresh_platform_status
        yield PlatformStatusState.check_connection

    @rx.event(background=True)
    async def refresh_platform_status(self):
        """Fetch the current status of the platform from the backend."""
        if not self.current_uid or self.current_uid not in self.platforms:
            return

        # Use the lock to prevent concurrent status checks
        if _status_lock.locked():
            logger.debug("Status check already in progress, skipping")
            return

        async with _status_lock:
            working_platform: Instance = self.working_platform

            # For brand-new platforms with no host configured, skip status check
            host_id = working_platform.safe_host_entry.get("id", "") if working_platform.safe_host_entry else ""
            if (working_platform.new_instance or not working_platform.platform.in_file) and not host_id:
                async with self:
                    self._platform_status = {
                        "platform_id": working_platform.platform.config.instance_name,
                        "state": "not deployed",
                        "host_configured": False,
                        "keys_verified": False,
                        "agents": {}
                    }
                    self._status_loading = False
                return

            # Set loading state and push to UI immediately
            async with self:
                self._status_loading = True
                self._status_error = ""
            yield  # Flush loading state to frontend before the potentially slow API call

            try:
                status_response = await get_platform_status(working_platform.platform.config.instance_name)
                async with self:
                    self._platform_status = status_response.dict() if hasattr(status_response, 'dict') else status_response
                    self._last_status_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    logger.debug(f"Platform status: {self._platform_status}")

                    # Auto-detect deployed status: if platform is running or deployed state detected,
                    # update the deployed flag (for platforms deployed before this fix)
                    detected_state = self._platform_status.get("state", "unknown")
                    if detected_state in ["running", "deployed"] and not working_platform.deployed:
                        logger.info(f"Auto-detecting deployed status for {working_platform.platform.config.instance_name}")
                        working_platform.deployed = True
                        # Persist the deployed flag to backend
                        try:
                            await mark_platform_deployed(working_platform.platform.config.instance_name, True)
                        except Exception as mark_err:
                            logger.warning(f"Could not persist deployed status: {mark_err}")
            except Exception as e:
                logger.error(f"Error fetching platform status: {e}")
                async with self:
                    self._status_error = str(e)
                    # If not marked as deployed and we get an error, show as not deployed
                    if not working_platform.deployed:
                        self._platform_status = {
                            "platform_id": working_platform.platform.config.instance_name,
                            "state": "not deployed",
                            "host_configured": False,
                            "keys_verified": False,
                            "agents": {}
                        }
                    else:
                        self._platform_status = {
                            "platform_id": working_platform.platform.config.instance_name,
                            "state": "unknown",
                            "host_configured": False,
                            "keys_verified": False,
                            "agents": {}
                        }
            finally:
                async with self:
                    self._status_loading = False

    @rx.event
    async def check_connection(self):
        """Check the connection to the platform host"""
        if not self.current_uid or self.current_uid not in self.platforms:
            return

        working_platform: Instance = self.working_platform

        # Only check for saved platforms (not new/unsaved ones)
        if working_platform.new_instance or not working_platform.platform.in_file:
            self._connection_status = "unknown"
            self._connection_method = "Platform not saved"
            return

        # Skip check if platform isn't deployed and has no host configured
        host_id = working_platform.safe_host_entry.get("id", "") if working_platform.safe_host_entry else ""
        if not working_platform.deployed and not host_id:
            self._connection_status = "unknown"
            self._connection_method = "Platform not deployed"
            return

        self._connection_status = "checking"

        try:
            result = await check_platform_connection(working_platform.platform.config.instance_name)

            if result.get("connected", False):
                self._connection_status = "connected"
                self._connection_method = result.get("connection_method", "Unknown method")
                self._connection_error = ""
            else:
                self._connection_status = "disconnected"
                self._connection_error = result.get("error", "Connection failed")

            self._last_connection_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"Error checking connection: {e}")
            self._connection_status = "disconnected"
            self._connection_error = str(e)

    @rx.event(background=True)
    async def handle_start_platform(self):
        """Start the VOLTTRON platform"""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return

            working_platform: Instance = self.working_platform

            if not working_platform.deployed:
                yield rx.toast.error("Platform must be deployed before starting")
                return

            # Show starting state
            self._starting_platform = True

        yield

        try:
            response = await start_platform(working_platform.platform.config.instance_name)
            response_data = response.json() if hasattr(response, 'json') else response

            # If backend says it's already running, we can finish immediately.
            if response_data.get("already_running", False):
                async with self:
                    self._starting_platform = False
                    self._platform_status["state"] = "running"
                yield rx.toast.info("VOLTTRON is already running!")
                yield PlatformStatusState.refresh_platform_status
                return

            # Poll status for up to 30s so startup has time to complete.
            deadline = asyncio.get_event_loop().time() + START_STOP_TIMEOUT_SECONDS
            started = False
            last_state = "unknown"
            while asyncio.get_event_loop().time() < deadline:
                try:
                    status_response = await get_platform_status(working_platform.platform.config.instance_name)
                    status_dict = status_response.dict() if hasattr(status_response, "dict") else status_response
                    last_state = status_dict.get("state", "unknown")
                    if last_state == "running":
                        started = True
                        break
                except Exception as poll_err:
                    logger.debug(f"[START_POLL] status check failed during startup: {poll_err}")
                await asyncio.sleep(START_STOP_POLL_INTERVAL_SECONDS)

            async with self:
                self._starting_platform = False
                if started:
                    self._platform_status["state"] = "running"

            if started:
                yield rx.toast.success("Platform started successfully!")
            else:
                yield rx.toast.error(
                    f"Start command sent, but platform did not report running within "
                    f"{START_STOP_TIMEOUT_SECONDS} seconds (last state: {last_state})."
                )

            yield PlatformStatusState.refresh_platform_status

        except ApiError as e:
            async with self:
                self._starting_platform = False

            yield rx.toast.error(f"Failed to start platform: {e.detail}")
        except Exception as e:
            async with self:
                self._starting_platform = False

            yield rx.toast.error(f"Error starting platform: {str(e)}")

    @rx.event(background=True)
    async def handle_stop_platform(self):
        """Stop the VOLTTRON platform"""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return

            working_platform: Instance = self.working_platform

            if not working_platform.deployed:
                yield rx.toast.error("Platform must be deployed before stopping")
                return

            # Show stopping state
            self._stopping_platform = True

        yield

        try:
            await stop_platform(working_platform.platform.config.instance_name)

            # Poll status for up to 30s so shutdown has time to complete.
            deadline = asyncio.get_event_loop().time() + START_STOP_TIMEOUT_SECONDS
            stopped = False
            last_state = "unknown"
            while asyncio.get_event_loop().time() < deadline:
                try:
                    status_response = await get_platform_status(working_platform.platform.config.instance_name)
                    status_dict = status_response.dict() if hasattr(status_response, "dict") else status_response
                    last_state = status_dict.get("state", "unknown")
                    if last_state != "running":
                        stopped = True
                        break
                except Exception as poll_err:
                    # After stopping, endpoint checks can fail transiently; treat as likely stopped.
                    logger.debug(f"[STOP_POLL] status check failed during shutdown: {poll_err}")
                    stopped = True
                    break
                await asyncio.sleep(START_STOP_POLL_INTERVAL_SECONDS)

            async with self:
                self._stopping_platform = False
                if stopped:
                    self._platform_status["state"] = "deployed"

            if stopped:
                yield rx.toast.success("Platform stopped successfully!")
            else:
                yield rx.toast.error(
                    f"Stop command sent, but platform still appears running after "
                    f"{START_STOP_TIMEOUT_SECONDS} seconds (last state: {last_state})."
                )

            yield PlatformStatusState.refresh_platform_status

        except ApiError as e:
            async with self:
                self._stopping_platform = False

            yield rx.toast.error(f"Failed to stop platform: {e.detail}")
        except Exception as e:
            async with self:
                self._stopping_platform = False

            yield rx.toast.error(f"Error stopping platform: {str(e)}")