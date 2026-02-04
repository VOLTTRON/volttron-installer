import reflex as rx
import asyncio
from loguru import logger
from ..models import Instance
from ..thin_endpoint_wrappers import install_agent, remove_agent, start_agent, stop_agent, get_platform_status, ApiError

from .platform_status import PlatformStatusState

class PlatformAgentState(PlatformStatusState):
    # Install agent dialog
    _show_install_agent_dialog: bool = False
    _install_agent_mode: str = "catalog"  # "catalog" or "manual"
    _install_agent_identity: str = ""
    _install_agent_source: str = ""
    _install_agent_start: bool = True
    _installing_agent: bool = False
    removing_agent_uuid: str = ""  # UUID of agent currently being removed
    starting_agent_uuid: str = ""  # UUID of agent currently being started
    stopping_agent_uuid: str = ""  # UUID of agent currently being stopped
    _selected_catalog_agent: str = ""  # identity of selected agent from catalog
    _show_remove_agent_dialog: bool = False
    _agent_to_remove_uuid: str = ""
    _agent_to_remove_name: str = ""

    @rx.var
    def install_agent_mode(self) -> str:
        return self._install_agent_mode
    
    @rx.var
    def install_agent_identity(self) -> str:
        """Autofill agent identity based on source if not explicitly set"""
        if self._install_agent_identity:
            return self._install_agent_identity
        
        # Try to infer from source for convenience
        src = self._install_agent_source
        if src:
            if "/" in src:
                return src.split("/")[-1].replace(".whl", "").replace("_", "-")
            elif "volttron-" in src:
                return src.replace("volttron-", "")
        return ""
    
    @rx.var
    def install_agent_source(self) -> str:
        return self._install_agent_source
    
    @rx.var
    def install_agent_start(self) -> bool:
        return self._install_agent_start
    
    @rx.var
    def installing_agent(self) -> bool:
        return self._installing_agent

    @rx.var
    def selected_catalog_agent(self) -> str:
        return self._selected_catalog_agent
    
    @rx.var
    def can_install_agent(self) -> bool:
        if self._install_agent_mode == "catalog":
            return self._selected_catalog_agent != ""
        else:
            return self._install_agent_identity != "" and self._install_agent_source != ""

    @rx.event
    def open_install_agent_dialog(self):
        """Open the install agent dialog"""
        self._show_install_agent_dialog = True
        self._install_agent_mode = "catalog"
        self._install_agent_identity = ""
        self._install_agent_source = ""
        self._selected_catalog_agent = ""

    @rx.event
    def close_install_agent_dialog(self, open_state: bool = False):
        if not open_state:
            self._show_install_agent_dialog = False

    @rx.event
    def set_install_agent_mode(self, mode: str):
        self._install_agent_mode = mode

    @rx.event
    def set_install_agent_identity(self, value: str):
        self._install_agent_identity = value

    @rx.event
    def set_install_agent_source(self, value: str):
        self._install_agent_source = value
        # Auto-set identity if empty
        if not self._install_agent_identity:
            if "/" in value:
                self._install_agent_identity = value.split("/")[-1].replace(".whl", "").replace("_", "-")
            elif "volttron-" in value:
                self._install_agent_identity = value.replace("volttron-", "")

    @rx.event
    def select_catalog_agent(self, identity: str):
        self._selected_catalog_agent = identity
        # Also pre-fill fields for manual mode just in case they switch
        for agent in self.list_of_agents:
            if agent.identity == identity:
                self._install_agent_identity = agent.identity
                self._install_agent_source = agent.source
                break

    @rx.event
    def set_install_agent_start(self, value: bool):
        self._install_agent_start = value

    @rx.event(background=True)
    async def handle_install_agent(self):
        """Install an agent on the running platform"""
        async with self:
            # Get agent details based on mode
            if self._install_agent_mode == "catalog":
                # Find the selected agent from the catalog
                selected_agent = None
                for agent in self.list_of_agents:
                    if agent.identity == self._selected_catalog_agent:
                        selected_agent = agent
                        break

                if not selected_agent:
                    yield rx.toast.error("Please select an agent from the catalog")
                    return

                agent_identity = selected_agent.identity
                agent_source = selected_agent.source
            else:
                # Manual mode
                if not self._install_agent_identity or not self._install_agent_source:
                    yield rx.toast.error("Please enter agent identity and source")
                    return

                agent_identity = self._install_agent_identity
                agent_source = self._install_agent_source

            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return

            working_platform: Instance = self.working_platform
            self._installing_agent = True

        yield

        try:
            await install_agent(
                platform_id=working_platform.platform.config.instance_name,
                agent_identity=agent_identity,
                agent_source=agent_source,
                start_agent=self._install_agent_start
            )

            async with self:
                self._installing_agent = False
                self._show_install_agent_dialog = False

            yield rx.toast.success(f"Agent {agent_identity} installed successfully!")
            yield PlatformStatusState.refresh_platform_status

        except ApiError as e:
            async with self:
                self._installing_agent = False
            yield rx.toast.error(f"Failed to install agent: {e.detail}")
        except Exception as e:
            async with self:
                self._installing_agent = False
            yield rx.toast.error(f"Error installing agent: {str(e)}")

    @rx.event
    def open_remove_agent_dialog(self, agent_uuid: str, agent_name: str):
        """Open confirmation dialog before removing agent"""
        logger.info(f"[REMOVE_DIALOG] Opening dialog for agent: {agent_name} ({agent_uuid})")
        self._agent_to_remove_uuid = agent_uuid
        self._agent_to_remove_name = agent_name
        self._show_remove_agent_dialog = True
        logger.info(f"[REMOVE_DIALOG] Dialog state set to: {self._show_remove_agent_dialog}")

    @rx.event
    def close_remove_agent_dialog(self, open_state: bool = False):
        """Close the remove agent confirmation dialog"""
        if not open_state:
            self._show_remove_agent_dialog = False
            self._agent_to_remove_uuid = ""
            self._agent_to_remove_name = ""

    @rx.event(background=True)
    async def confirm_remove_agent(self):
        """Actually remove the agent after confirmation"""
        
        # Check if status check is in progress to prevent VOLTTRON corruption
        async with self:
            if self._status_check_in_progress:
                yield rx.toast.warning("System busy with status check, please wait...")
                return
            
            self._status_check_in_progress = True
            agent_uuid = self._agent_to_remove_uuid
            
            if not self.current_uid or self.current_uid not in self.platforms:
                self._status_check_in_progress = False
                yield rx.toast.error("Platform not found")
                return

            working_platform: Instance = self.working_platform
            self.removing_agent_uuid = agent_uuid
            self._show_remove_agent_dialog = False

        yield

        try:
            await remove_agent(
                platform_id=working_platform.platform.config.instance_name,
                agent_uuid=agent_uuid
            )

            async with self:
                self.removing_agent_uuid = ""
                self._agent_to_remove_uuid = ""
                self._agent_to_remove_name = ""
                
                # Optimistic update: remove from status dict if present
                if self._platform_status and "agents" in self._platform_status:
                    agents = self._platform_status["agents"]
                    key_to_remove = None
                    for k, v in agents.items():
                        if v.get("uuid") == agent_uuid:
                            key_to_remove = k
                            break
                    if key_to_remove:
                        status = self._platform_status.copy()
                        status["agents"] = {k: v for k, v in status["agents"].items() if k != key_to_remove}
                        self._platform_status = status

            yield rx.toast.success(f"Agent removed successfully!")
            yield PlatformStatusState.refresh_platform_status_debounced

        except ApiError as e:
            async with self:
                self.removing_agent_uuid = ""
            yield rx.toast.error(f"Failed to remove agent: {e.detail}")
        except Exception as e:
            async with self:
                self.removing_agent_uuid = ""
            yield rx.toast.error(f"Error removing agent: {str(e)}")
        finally:
            async with self:
                self._status_check_in_progress = False

    @rx.event(background=True)
    async def handle_start_agent(self, agent_id: str):
        """Start a specific agent"""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return

            working_platform: Instance = self.working_platform
            platform_name = working_platform.platform.config.instance_name
            logger.info(f"[START_AGENT_UI] Setting starting UUID to: {agent_id}")
            self.starting_agent_uuid = agent_id

        yield rx.call_script("void(0)")  # Force UI update to show spinner

        try:
            await start_agent(platform_name, agent_id)

            # Poll for status update
            for i in range(15):  # 15 seconds timeout
                await asyncio.sleep(1)
                
                # Respect lock to prevent VOLTTRON corruption
                if self._status_check_in_progress:
                    continue

                try:
                    async with self:
                        self._status_check_in_progress = True
                    
                    status_response = await get_platform_status(platform_name)
                    status = status_response.dict() if hasattr(status_response, 'dict') else status_response
                    
                    # Update global status 
                    async with self:
                        self._platform_status = status
                    
                    # Check agent state
                    agents = status.get("agents", {})
                    # Find agent by UUID since agents dict is keyed by identity
                    agent_info = {}
                    for a_data in agents.values():
                        if a_data.get("uuid") == agent_id:
                            agent_info = a_data
                            break
                    
                    if agent_info.get("state") == "running":
                        async with self:
                            self.starting_agent_uuid = "" 
                        yield rx.call_script("void(0)")
                        yield rx.toast.success(f"Agent started successfully!")
                        return 
                except Exception as poll_error:
                    logger.debug(f"Error polling status: {poll_error}")
                finally:
                    async with self:
                        self._status_check_in_progress = False

            # Timeout
            async with self:
                self.starting_agent_uuid = ""
            yield rx.call_script("void(0)")
            yield rx.toast.warning("Agent start command sent but status update timed out.")
            yield self.refresh_platform_status_debounced()

        except ApiError as e:
            async with self:
                self.starting_agent_uuid = ""
            yield rx.call_script("void(0)")  # Force UI update
            yield rx.toast.error(f"Failed to start agent: {e.detail}")
        except Exception as e:
            async with self:
                self.starting_agent_uuid = ""
            yield rx.call_script("void(0)")  # Force UI update
            yield rx.toast.error(f"Error starting agent: {str(e)}")

    @rx.event(background=True)
    async def handle_stop_agent(self, agent_id: str):
        """Stop a specific agent"""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return

            working_platform: Instance = self.working_platform
            platform_name = working_platform.platform.config.instance_name
            logger.info(f"[STOP_AGENT_UI] Setting stopping UUID to: {agent_id}")
            self.stopping_agent_uuid = agent_id

        yield rx.call_script("void(0)")  # Force UI update to show spinner

        try:
            await stop_agent(platform_name, agent_id)

            # Poll for status update
            for i in range(15):  # 15 seconds timeout
                await asyncio.sleep(1)
                
                # Respect lock to prevent VOLTTRON corruption
                if self._status_check_in_progress:
                    continue

                try:
                    async with self:
                        self._status_check_in_progress = True
                    status_response = await get_platform_status(platform_name)
                    status = status_response.dict() if hasattr(status_response, 'dict') else status_response
                    
                    # Update global status 
                    async with self:
                        self._platform_status = status
                    
                    # Check agent state
                    agents = status.get("agents", {})
                    # Find agent by UUID since agents dict is keyed by identity
                    agent_info = {}
                    for a_data in agents.values():
                        if a_data.get("uuid") == agent_id:
                            agent_info = a_data
                            break
                    
                    if agent_info.get("state") != "running":
                        async with self:
                            self.stopping_agent_uuid = ""
                        yield rx.call_script("void(0)")
                        yield rx.toast.success(f"Agent stopped successfully!")
                        return
                except Exception as poll_error:
                    logger.debug(f"Error polling status: {poll_error}")
                finally:
                    async with self:
                        self._status_check_in_progress = False

            # Timeout
            async with self:
                self.stopping_agent_uuid = ""
            yield rx.call_script("void(0)")
            yield rx.toast.warning("Agent stop command sent but status update timed out.")
            yield self.refresh_platform_status_debounced()

        except ApiError as e:
            async with self:
                self.stopping_agent_uuid = ""
            yield rx.call_script("void(0)")  # Force UI update
            yield rx.toast.error(f"Failed to stop agent: {e.detail}")
        except Exception as e:
            async with self:
                self.stopping_agent_uuid = ""
            yield rx.call_script("void(0)")  # Force UI update
            yield rx.toast.error(f"Error stopping agent: {str(e)}")
