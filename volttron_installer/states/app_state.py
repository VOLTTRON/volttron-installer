"""AppState, ToolState, and SettingsState - UI shell, tool lifecycle, and app settings."""

import reflex as rx
import subprocess
import asyncio
from loguru import logger
from typing import Optional

from ..settings import get_settings
from ..backend.models import ToolRequest, ToolStatusResponse
from ..thin_endpoint_wrappers import start_tool, stop_tool, tool_status


class AppState(rx.State):
    """The app state."""
    _sidebar_page_selected: str = "home"
    tool_accordion_value: str ="tools"

    # Events
    @rx.var
    def sidebar_selected_page(self) -> str:
        self._sidebar_page_selected = self.router.page.raw_path if self.router.page.raw_path != "/" else "home"
        logger.debug(self._sidebar_page_selected)
        return self._sidebar_page_selected

    @rx.event
    def toggle_tool_dropdown(self, value: str):
        """Toggle the tool dropdown."""
        self.tool_accordion_value = value

    @rx.event
    def select_bacnet_scan(self):
        self.sidebar_page_selected = "bacnet_scan"
        # yield NavigationState.route_to_bacnet_scan()

    @rx.event
    def select_instances(self):
        self.sidebar_page_selected = "instances"
        # yield NavigationState.route_to_index()


class ToolState(rx.State):
    """State for managing tool lifecycle."""

    # Track running tools
    _running_tools: dict[str, bool] = {}
    loading_tools: dict[str, bool] = {}
    error_message: Optional[str] = None

    # Tool configuration
    tool_configs: dict[str, ToolRequest] = {
        "bacnet_scan_api": ToolRequest(
            tool_name="bacnet_scan_api",
            module_path="bacnet_scan_api.main:app",
        ),
        # Add other tools as we go
    }

    # Computed var to make sure we are accessing running tool
    @rx.var
    def running_tools(self) -> dict[str, bool]:
        return self._running_tools

    @rx.event(background=True)
    async def monitor_all_tools(self):
        while True:
            await asyncio.sleep(5)
            async with self:
                for tool_id in self.tool_configs:
                    try:
                        status = await tool_status(tool_id)
                        self._running_tools[tool_id] = status.tool_running
                    except Exception as e:
                        self._running_tools[tool_id] = False

    @rx.event(background=True)
    async def start_tool(self, tool_id: str):
        """Start a specific tool service."""
        logger.debug(f"starting tool : {tool_id}")

        async with self:
            if tool_id not in self.tool_configs:
                logger.debug(f"Unknown tool: {tool_id}")
                return

            # Check if already running
            if self._running_tools.get(tool_id, False):
                logger.debug("tool is already running")
                return

            # Set loading state
            logger.debug(f"setting tool to loading: {tool_id}")
            self.loading_tools[tool_id] = True

        try:
            # Get tool config
            async with self:
                config = self.tool_configs[tool_id]

            logger.debug("calling api...")
            # Call API to start the tool
            await start_tool(config)

            async with self:
                self._running_tools[tool_id] = True
                self.loading_tools[tool_id] = False

            logger.debug("tool started")

            yield ToolState.monitor_all_tools()
        except Exception as e:
            logger.debug(f"Error starting tool: {str(e)}")
            async with self:
                self.loading_tools[tool_id] = False


    @rx.event
    async def stop_tool(self, tool_id: str) -> None:
        """Stop a specific tool service."""
        logger.debug(f"stopping tool : {tool_id}")
        if tool_id not in self.tool_configs:
            logger.debug(f"Unknown tool: {tool_id}")
            return

        # Check if it's running
        # if not self.is_tool_running(tool_id):
        #     self._running_tools[tool_id] = False
        if not self._running_tools.get(tool_id, False):
            logger.debug("tool is already not running")
            return

        # Set loading state
        self.loading_tools[tool_id] = True

        try:
            # Call API to stop the tool
            await stop_tool(tool_id)
            self.running_tools[tool_id] = False
            logger.debug("tool stopped")

        except Exception as e:
            logger.debug(f"Error stopping tool: {str(e)}")
        finally:
            # Clear loading state
            self.loading_tools[tool_id] = False

    @rx.event
    async def check_tool_status(self, tool_id: str) -> None:
        """Check if a specific tool is running."""
        if tool_id not in self.tool_configs:
            return

        try:
            # Call API to get tool status
            tool_status: ToolStatusResponse = await tool_status(tool_id)
            self.running_tools[tool_id] = tool_status.tool_running
        except Exception as e:
            logger.debug(f"Error checking tool status: {str(e)}")

    @classmethod
    async def is_tool_running(self, tool_name: str) -> bool:
        try:
            response: ToolStatusResponse = await tool_status(tool_name)
            return response.tool_running
        except Exception as e:
            logger.debug(f"There was an error checking the tool status for `{tool_name}: {e}`")
            return False


settings = get_settings()


class SettingsState(rx.State):
    """The settings state."""

    app_name: str = settings.app_name
    secret_key: str = settings.secret_key

    _upload_dir: str = settings.upload_dir
    _data_dir: str = settings.data_dir