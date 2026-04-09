"""IndexPageState - Home page state."""

import reflex as rx
from loguru import logger


class IndexPageState(rx.State):
    """State for the Index page"""
    selected_tool: str = ""
    scanning_bacnet_range: bool = False
    is_starting_proxy: bool = False
    proxy_up: bool = False

    # Events
    @rx.event
    def toggle_proxy(self):
        """Toggle the proxy state"""
        if self.proxy_up:
            self.proxy_up = False
            yield rx.toast.success("Proxy stopped successfully.")
        else:
            yield IndexPageState.start_proxy()

    @rx.event
    async def start_proxy(self):
        """Handle the start proxy button click"""
        if self.is_starting_proxy:
            yield rx.toast.info("Proxy is already starting.")
            return
        self.is_starting_proxy = True
        yield rx.toast.success("Starting proxy...")
        # TODO implement proxy start logic
        import asyncio
        await asyncio.sleep(2)
        self.proxy_up = True
        self.is_starting_proxy = False
        yield rx.toast.success("Proxy started successfully.")

    @rx.event
    async def stop_proxy(self):
        pass

    @rx.event
    def set_selected_tool(self, tool: str):
        """Change the selected tool"""
        if self.selected_tool == tool:
            self.selected_tool = ""
        else:
            self.selected_tool = tool
        logger.debug(f"Selected tool changed to: {self.selected_tool}")