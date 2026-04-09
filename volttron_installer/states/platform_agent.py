import reflex as rx
from loguru import logger
from ..models import Instance
from ..model_views import AgentModelView
from ..thin_endpoint_wrappers import (
    install_agent, remove_agent, start_agent, stop_agent,
    get_github_agents, get_local_agents, ApiError,
)

from .platform_status import PlatformStatusState, _status_lock

class PlatformAgentState(PlatformStatusState):
    # Install agent dialog
    _show_install_agent_dialog: bool = False
    _install_agent_mode: str = "catalog"  # "catalog", "local", or "manual"
    _install_agent_identity: str = ""
    _install_agent_source: str = ""
    _install_agent_start: bool = True
    _installing_agent: bool = False
    removing_agent_uuid: str = ""  # UUID of agent currently being removed
    starting_agent_uuid: str = ""  # UUID of agent currently being started
    stopping_agent_uuid: str = ""  # UUID of agent currently being stopped
    _selected_catalog_agent: str = ""  # identity of selected agent from catalog
    _selected_local_agent: str = ""    # identity of selected local workspace agent
    _show_remove_agent_dialog: bool = False
    _agent_to_remove_uuid: str = ""
    _agent_to_remove_name: str = ""
    _agent_action_message: str = ""  # Status message shown while agent actions are in flight

    @rx.var
    def show_install_agent_dialog(self) -> bool:
        return self._show_install_agent_dialog

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
    def selected_local_agent(self) -> str:
        return self._selected_local_agent

    @rx.var
    def can_install_agent(self) -> bool:
        if self._install_agent_mode == "catalog":
            return self._selected_catalog_agent != ""
        elif self._install_agent_mode == "local":
            return self._selected_local_agent != ""
        else:  # manual
            return self._install_agent_identity != "" and self._install_agent_source != ""

    @rx.var
    def agent_action_message(self) -> str:
        return self._agent_action_message

    @rx.event
    def open_install_agent_dialog(self):
        """Open the install agent dialog and trigger background fetches."""
        self._show_install_agent_dialog = True
        self._install_agent_mode = "catalog"
        self._install_agent_identity = ""
        self._install_agent_source = ""
        self._selected_catalog_agent = ""
        self._selected_local_agent = ""
        return [
            PlatformAgentState.fetch_github_agents,
            PlatformAgentState.load_local_agents,
        ]

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
        # Pre-fill manual fields in case the user switches modes
        for agent in self.github_agents:
            if agent.identity == identity:
                self._install_agent_identity = agent.identity
                self._install_agent_source = agent.source
                return
        for agent in self.list_of_agents:
            if agent.identity == identity:
                self._install_agent_identity = agent.identity
                self._install_agent_source = agent.source
                return

    @rx.event
    def select_local_agent(self, identity: str):
        """Select a local workspace agent for installation."""
        self._selected_local_agent = identity
        # Pre-fill manual fields in case the user switches modes
        for agent in self.local_agents:
            if agent.identity == identity:
                self._install_agent_identity = agent.identity
                self._install_agent_source = agent.local_path
                return

    @rx.event
    def set_install_agent_start(self, value: bool):
        self._install_agent_start = value

    @rx.event(background=True)
    async def fetch_github_agents(self):
        """Background event: fetch modular VOLTTRON agents from eclipse-volttron GitHub org."""
        async with self:
            self.github_agents_loading = True
            self.github_agents_offline = False

        try:
            result = await get_github_agents()
            agent_views: list[AgentModelView] = []
            for agent in result.agents:
                desc = agent.default_config.get("_description", "") if isinstance(agent.default_config, dict) else ""
                agent_views.append(AgentModelView(
                    identity=agent.identity,
                    source=agent.source or "",
                    config="{}",
                    config_store=[],
                    routing_id=agent.identity,
                    description=desc,
                    config_store_allowed=agent.config_store_allowed,
                    safe_agent={
                        "identity": agent.identity,
                        "source": agent.source or "",
                        "config": "{}",
                        "config_store": {},
                    },
                ))
            async with self:
                self.github_agents = agent_views
                self.github_agents_loading = False
                self.github_agents_offline = result.offline
        except Exception as exc:
            logger.error(f"Failed to fetch GitHub agents: {exc}")
            async with self:
                self.github_agents = []
                self.github_agents_loading = False
                self.github_agents_offline = True

    @rx.event(background=True)
    async def load_local_agents(self):
        """Background event: scan the local workspace for custom agent directories."""
        async with self:
            self.local_agents_loading = True

        try:
            agents = await get_local_agents()
            agent_views: list[AgentModelView] = []
            for agent in agents:
                desc = agent.default_config.get("_description", "") if isinstance(agent.default_config, dict) else ""
                agent_views.append(AgentModelView(
                    identity=agent.identity,
                    source=agent.source or "",
                    config="{}",
                    config_store=[],
                    routing_id=agent.identity,
                    is_local=True,
                    local_path=agent.local_path or agent.source or "",
                    description=desc,
                    config_store_allowed=False,
                    safe_agent={
                        "identity": agent.identity,
                        "source": agent.source or "",
                        "config": "{}",
                        "config_store": {},
                    },
                ))
            async with self:
                self.local_agents = agent_views
                self.local_agents_loading = False
        except Exception as exc:
            logger.warning(f"Failed to load local agents: {exc}")
            async with self:
                self.local_agents = []
                self.local_agents_loading = False

    @rx.event(background=True)
    async def handle_install_agent(self):
        """Install an agent on the running platform"""
        async with self:
            # Get agent details based on mode
            if self._install_agent_mode == "catalog":
                # Search github_agents first, fall back to hardcoded list_of_agents
                selected_agent = None
                for agent in self.github_agents:
                    if agent.identity == self._selected_catalog_agent:
                        selected_agent = agent
                        break
                if selected_agent is None:
                    for agent in self.list_of_agents:
                        if agent.identity == self._selected_catalog_agent:
                            selected_agent = agent
                            break

                if not selected_agent:
                    yield rx.toast.error("Please select an agent from the catalog")
                    return

                agent_identity = selected_agent.identity
                agent_source = selected_agent.source

            elif self._install_agent_mode == "local":
                selected_agent = None
                for agent in self.local_agents:
                    if agent.identity == self._selected_local_agent:
                        selected_agent = agent
                        break

                if not selected_agent:
                    yield rx.toast.error("Please select a local agent")
                    return

                agent_identity = selected_agent.identity
                agent_source = selected_agent.local_path  # absolute path on disk

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
        """Remove the agent after confirmation"""
        # Check if a status check is already in progress
        if _status_lock.locked():
            yield rx.toast.warning("System busy with status check, please wait...")
            return

        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return

            working_platform: Instance = self.working_platform
            agent_uuid = self._agent_to_remove_uuid
            self.removing_agent_uuid = agent_uuid
            self._show_remove_agent_dialog = False
            self._agent_action_message = f"Removing agent {self._agent_to_remove_name}..."

        try:
            await remove_agent(
                platform_id=working_platform.platform.config.instance_name,
                agent_uuid=agent_uuid
            )

            async with self:
                self.removing_agent_uuid = ""
                self._agent_to_remove_uuid = ""
                self._agent_to_remove_name = ""
                self._agent_action_message = ""

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

            yield rx.toast.success("Agent removed successfully!")
            yield PlatformStatusState.refresh_platform_status_debounced

        except ApiError as e:
            async with self:
                self.removing_agent_uuid = ""
                self._agent_action_message = ""
            yield rx.toast.error(f"Failed to remove agent: {e.detail}")
        except Exception as e:
            async with self:
                self.removing_agent_uuid = ""
                self._agent_action_message = ""
            yield rx.toast.error(f"Error removing agent: {str(e)}")

    @rx.event(background=True)
    async def handle_start_agent(self, agent_id: str):
        """Start a specific agent — fire and forget with debounced status refresh."""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return

            working_platform: Instance = self.working_platform
            platform_name = working_platform.platform.config.instance_name
            self.starting_agent_uuid = agent_id
            self._agent_action_message = f"Starting agent..."

        try:
            await start_agent(platform_name, agent_id)
            async with self:
                self.starting_agent_uuid = ""
                self._agent_action_message = ""
            yield rx.toast.success("Start command sent. Refreshing status...")
            yield PlatformStatusState.refresh_platform_status_debounced

        except ApiError as e:
            async with self:
                self.starting_agent_uuid = ""
                self._agent_action_message = ""
            yield rx.toast.error(f"Failed to start agent: {e.detail}")
        except Exception as e:
            async with self:
                self.starting_agent_uuid = ""
                self._agent_action_message = ""
            yield rx.toast.error(f"Error starting agent: {str(e)}")

    @rx.event(background=True)
    async def handle_stop_agent(self, agent_id: str):
        """Stop a specific agent — fire and forget with debounced status refresh."""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                yield rx.toast.error("Platform not found")
                return

            working_platform: Instance = self.working_platform
            platform_name = working_platform.platform.config.instance_name
            self.stopping_agent_uuid = agent_id
            self._agent_action_message = f"Stopping agent..."

        try:
            await stop_agent(platform_name, agent_id)
            async with self:
                self.stopping_agent_uuid = ""
                self._agent_action_message = ""
            yield rx.toast.success("Stop command sent. Refreshing status...")
            yield PlatformStatusState.refresh_platform_status_debounced

        except ApiError as e:
            async with self:
                self.stopping_agent_uuid = ""
                self._agent_action_message = ""
            yield rx.toast.error(f"Failed to stop agent: {e.detail}")
        except Exception as e:
            async with self:
                self.stopping_agent_uuid = ""
                self._agent_action_message = ""
            yield rx.toast.error(f"Error stopping agent: {str(e)}")