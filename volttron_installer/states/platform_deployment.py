import reflex as rx
import asyncio
import json
from loguru import logger
from ..models import Instance
from ..backend.models import CreatePlatformRequest, PlatformConfig, AgentDefinition, ConfigStoreEntry
from ..thin_endpoint_wrappers import update_platform, deploy_platform, get_deploy_progress, install_python310, mark_platform_deployed

from .platform_agent import PlatformAgentState
from .platform_status import PlatformStatusState

class PlatformDeploymentState(PlatformAgentState):
    # Deployment progress tracking
    _is_deploying: bool = False
    _deployment_status: str = "idle"  # idle, running, success, failed
    _deployment_logs: list[str] = []
    _current_task: str = ""
    _deployment_progress: int = 0  # 0-100
    _show_deployment_dialog: bool = False
    _deployment_steps: list[dict] = []

    # Pyenv install dialog
    _show_pyenv_dialog: bool = False
    _pyenv_installing: bool = False
    _pyenv_error: str = ""

    # === vars for deployment progress ===
    @rx.var
    def is_deploying(self) -> bool:
        return self._is_deploying
    
    @rx.var
    def deployment_status(self) -> str:
        return self._deployment_status
    
    @rx.var
    def deployment_logs(self) -> list[str]:
        return self._deployment_logs
    
    @rx.var
    def current_task(self) -> str:
        return self._current_task
    
    @rx.var
    def deployment_progress(self) -> int:
        return self._deployment_progress

    @rx.var
    def deployment_steps(self) -> list[dict]:
        return self._deployment_steps
    
    @rx.var
    def show_deployment_dialog(self) -> bool:
        return self._show_deployment_dialog
    
    @rx.var
    def show_pyenv_dialog(self) -> bool:
        return self._show_pyenv_dialog

    @rx.var
    def pyenv_installing(self) -> bool:
        return self._pyenv_installing

    @rx.var
    def pyenv_error(self) -> str:
        return self._pyenv_error

    @rx.var
    def show_pyenv_prompt(self) -> bool:
        result = False
        if self._show_pyenv_dialog:
            result = True
        elif self._pyenv_error:
            result = True
        elif any("Unsupported Python version" in log for log in self._deployment_logs):
            result = True
        logger.debug(f"[PYENV_PROMPT] show_pyenv_prompt={result}, _show_pyenv_dialog={self._show_pyenv_dialog}, _pyenv_error={bool(self._pyenv_error)}")
        return result

    def close_deployment_dialog(self):
        """Close the deployment progress dialog"""
        self._show_deployment_dialog = False

    @rx.event
    def close_pyenv_dialog(self):
        self._show_pyenv_dialog = False
        self._pyenv_error = ""

    @rx.event(background=True)
    async def handle_deploy(self):
        working_platform: Instance = self.platforms[self.current_uid]

        # Show deployment dialog and initialize state
        async with self:
            self._show_deployment_dialog = True
            self._is_deploying = True
            self._deployment_status = "running"
            self._deployment_logs = []
            self._deployment_steps = []
            self._current_task = "Saving platform configuration..."
            self._deployment_progress = 0
        yield

        try:
            # Save platform config to backend before deploying
            # This ensures any UI changes (like volttron_version) are persisted
            # Convert frontend model views to backend models
            config_dict = working_platform.platform.config.to_dict()
            logger.info(f"[DEPLOY SAVE] Config dict volttron_version: {config_dict.get('volttron_version', 'NOT FOUND')}")
            logger.info(f"[DEPLOY SAVE] Full config_dict: {config_dict}")

            agents_dict = {}
            for agent_id, agent_view in working_platform.platform.agents.items():
                agent_data = agent_view.to_dict()
                # AgentDefinition requires pypi_package or source - use source field
                agents_dict[agent_id] = AgentDefinition(
                    identity=agent_data["identity"],
                    source=agent_data.get("source"),
                    config=agent_data.get("config"),
                    config_store={
                        k: ConfigStoreEntry(**v) for k, v in agent_data.get("config_store", {}).items()
                    },
                    config_store_allowed=agent_data.get("config_store_allowed", True)
                )

            platform_request = CreatePlatformRequest(
                host_id=working_platform.host.id,
                config=PlatformConfig(**config_dict),
                agents=agents_dict,
                deployed=True  # Ensure deployed flag is set/preserved
            )
            logger.info(f"[DEPLOY SAVE] Saving platform with volttron_version: {platform_request.config.volttron_version}")
            await update_platform(working_platform.platform.config.instance_name, platform_request)
            logger.info(f"[DEPLOY SAVE] Platform saved successfully")
            async with self:
                self._current_task = "Deploying platform..."
                self._deployment_progress = 5
            yield

            deploy_task = asyncio.create_task(
                deploy_platform(working_platform.platform.config.instance_name, working_platform.password)
            )

            # Poll deploy progress while deployment runs
            while not deploy_task.done():
                try:
                    progress = await get_deploy_progress(working_platform.platform.config.instance_name)
                    async with self:
                        self._deployment_steps = progress.get("steps", [])
                        self._deployment_progress = progress.get("progress", self._deployment_progress)
                        self._current_task = progress.get("current_task", self._current_task)
                        logs = progress.get("logs", [])
                        if logs:
                            self._deployment_logs = logs[-200:]
                except Exception as poll_error:
                    async with self:
                        self._deployment_logs.append(f"Progress check failed: {poll_error}")
                        self._deployment_logs = self._deployment_logs[-200:]
                yield
                await asyncio.sleep(1)

            response = await deploy_task
            response_data = response.json()

            # Parse the output and extract task information
            output = response_data.get("output", "")
            tasks = response_data.get("tasks", [])

            async with self:
                for line in output.split('\n'):
                    if line.strip():
                        self._deployment_logs.append(line)
                self._deployment_logs = self._deployment_logs[-200:]

                # Mark as deployed and enable tabs
                working_platform.deployed = True
                working_platform.platform.in_file = True  # Enable Status and Logs tabs
                logger.debug(f"response: {response_data}")

                # Update deployment state to success
                self._deployment_status = "success"
                self._is_deploying = False
                self._current_task = f"Deployment completed successfully ({len(tasks)} tasks executed)"
                self._deployment_progress = 100
            
            # Persist deployed status to backend
            try:
                await mark_platform_deployed(working_platform.platform.config.instance_name, True)
                logger.info(f"[DEPLOY] Marked platform {working_platform.platform.config.instance_name} as deployed")
            except Exception as mark_err:
                logger.warning(f"[DEPLOY] Could not persist deployed status: {mark_err}")
            
            yield rx.toast.success("Deployed Successfully!")
            
            # Force refresh of platform status/connection to show updated deployment state
            await asyncio.sleep(1.0) # wait for file write to settle
            yield PlatformStatusState.load_platform_status_background
            
        except Exception as e:
            logger.error(f"[DEPLOY] Error deploying platform {working_platform.platform.config.instance_name}: {e}")
            error_text = str(e)
            # Also check for detail attribute on ApiError - may be JSON
            if hasattr(e, 'detail'):
                raw_detail = e.detail
                # Try to parse JSON response to get actual error message
                try:
                    parsed = json.loads(raw_detail)
                    if isinstance(parsed, dict) and "detail" in parsed:
                        error_text = parsed["detail"]
                    else:
                        error_text = raw_detail
                except (json.JSONDecodeError, TypeError):
                    error_text = raw_detail
                logger.error(f"[DEPLOY] Error detail: {error_text}")

            async with self:
                # Update deployment state to failed
                self._deployment_status = "failed"
                self._is_deploying = False
                self._current_task = f"Deployment failed"
                self._deployment_logs.append(f"ERROR: {error_text}")
                self._deployment_logs = self._deployment_logs[-200:]

                # Check if this is a Python version issue - show pyenv prompt
                if "Unsupported Python version" in error_text or "Python 3.10" in error_text:
                    logger.info(f"[DEPLOY] Python version issue detected, showing pyenv prompt")
                    self._show_pyenv_dialog = True
                    self._pyenv_error = "Python 3.10 is required but not found on the remote host."

    @rx.event(background=True)
    async def handle_install_pyenv(self):
        """Install Python 3.10 via pyenv on the remote host and create venv."""
        working_platform: Instance = self.platforms[self.current_uid]
        async with self:
            self._pyenv_installing = True
            self._pyenv_error = ""
        yield

        try:
            result = await install_python310(working_platform.platform.config.instance_name)
            logger.info(f"[PYENV] Install result: {result}")
            
            # Refresh platform data to get updated custom_python_path
            await self.hydrate_state()
            
            async with self:
                self._pyenv_installing = False
                self._show_pyenv_dialog = False
            yield rx.toast.success("Python 3.10 installed via pyenv. Click Deploy to continue.")
        except Exception as e:
            logger.error(f"[PYENV] Install failed: {e}")
            async with self:
                self._pyenv_installing = False
                # Extract the detail from ApiError if available
                error_msg = str(e)
                if hasattr(e, 'detail'):
                    error_msg = e.detail
                self._pyenv_error = error_msg
            yield rx.toast.error("Pyenv install failed. Check details in the dialog.")
