"""PlatformDialogState - Dialog state and handlers for delete, create, connect, password, and install agent dialogs."""

import reflex as rx
from loguru import logger

from ..models import Instance
from ..model_views import HostEntryModelView, PlatformModelView, PlatformConfigModelView
from ..backend.models import CreatePlatformRequest, PlatformConfig, CreateOrUpdateHostEntryRequest
from ..navigation.state import NavigationState
from ..thin_endpoint_wrappers import detect_existing_volttron, ApiError, delete_platform, add_host, create_platform, check_platform_connection, mark_platform_deployed

from .platform_validation import PlatformValidationState


class PlatformDialogState(PlatformValidationState):
    # Delete platform dialog
    _show_delete_dialog: bool = False
    _delete_remote_files: bool = False
    _delete_confirmed: bool = False
    _deleting_platform: bool = False

    # Create platform dialog (Deploy New vs Connect Existing)
    _show_create_platform_dialog: bool = False
    _connect_existing_mode: bool = False  # True when in "connect to existing" flow
    _detecting_volttron: bool = False  # True while detecting existing VOLTTRON
    _detected_volttron_home: str = ""
    _detected_volttron_venv: str = ""
    _detected_volttron_running: bool = False
    _connect_ssh_host: str = ""
    _connect_ssh_user: str = ""
    _connect_ssh_port: str = "22"

    # Remote deploy password dialog state
    show_password_dialog: bool = False
    deploy_password_error: str = ""
    checking_deploy_connection: bool = False

    @rx.event(background=True)
    async def on_platform_page_load(self):
        """Ensure platform data is hydrated and status is refreshed on page load."""
        await self.hydrate_state()
        async with self:
            wp = self.platforms.get(self.current_uid)
            if wp is None or not wp.platform.in_file:
                self.platform_nav = "setup"
            else:
                self.platform_nav = "overview"
        yield PlatformDialogState.load_platform_status_background

    # ---- Delete platform dialog ----

    @rx.var
    def show_delete_dialog(self) -> bool:
        return self._show_delete_dialog

    @rx.var
    def delete_remote_files(self) -> bool:
        return self._delete_remote_files

    @rx.var
    def delete_confirmed(self) -> bool:
        return self._delete_confirmed

    @rx.var
    def deleting_platform(self) -> bool:
        return self._deleting_platform

    @rx.event
    def open_delete_dialog(self):
        """Open the delete platform dialog (uses current_uid)."""
        self._show_delete_dialog = True
        self._delete_remote_files = False
        self._delete_confirmed = False

    @rx.event
    def open_delete_dialog_for_instance(self, instance_name: str):
        """Open the delete platform dialog for a specific instance."""
        self.current_uid = instance_name
        self._show_delete_dialog = True
        self._delete_remote_files = False
        self._delete_confirmed = False

    @rx.event
    def close_delete_dialog(self):
        """Close the delete platform dialog and reset state."""
        self._show_delete_dialog = False
        self._delete_remote_files = False
        self._delete_confirmed = False
        self._deleting_platform = False

    @rx.event
    def toggle_delete_remote_files(self, checked: bool):
        """Toggle whether to delete remote VOLTTRON files."""
        self._delete_remote_files = checked

    @rx.event
    def confirm_delete(self):
        """Move to the confirmation step."""
        self._delete_confirmed = True

    @rx.event
    def back_to_delete_options(self):
        """Go back to the options step."""
        self._delete_confirmed = False

    @rx.event(background=True)
    async def handle_delete_platform(self):
        """Delete the current platform — backend-first with spinner and rollback on failure."""
        from ..thin_endpoint_wrappers import delete_remote_volttron_files, remove_from_inventory

        async with self:
            working_platform: Instance = self.platforms.get(self.current_uid)
            if working_platform is None:
                yield rx.toast.error("No platform selected to delete")
                self._show_delete_dialog = False
                return

            instance_name = working_platform.platform.config.instance_name
            delete_remote = self._delete_remote_files
            uid_to_delete = self.current_uid
            platform_in_file = working_platform.platform.in_file
            host_id = working_platform.host.id

            # Show spinner in the confirmation dialog
            self._deleting_platform = True

        # --- Backend calls (dialog stays open showing spinner) ---

        errors: list[str] = []

        if delete_remote:
            try:
                await delete_remote_volttron_files(instance_name)
                logger.info(f"Deleted remote files for {instance_name}")
            except Exception as e:
                logger.error(f"Failed to delete remote files: {e}")
                errors.append(f"Remote files: {str(e)}")

        if platform_in_file and instance_name:
            try:
                await delete_platform(instance_name)
                logger.info(f"Deleted platform backend data for {instance_name}")
            except Exception as e:
                logger.warning(f"Platform files may not exist: {e}")
                errors.append(f"Platform data: {str(e)}")

            if host_id:
                try:
                    await remove_from_inventory(host_id)
                    logger.info(f"Deleted host entry for {instance_name}")
                except Exception as e:
                    logger.warning(f"Could not delete host entry: {e}")
                    errors.append(f"Host entry: {str(e)}")

        async with self:
            self._deleting_platform = False
            self._delete_remote_files = False
            self._delete_confirmed = False

            if not errors:
                # All backend calls succeeded — safe to remove from UI
                self._show_delete_dialog = False
                self.platforms = {k: v for k, v in self.platforms.items() if k != uid_to_delete}

        if not errors:
            yield rx.toast.success(f"Platform {instance_name} removed successfully")
            yield rx.redirect("/instances")
        else:
            error_summary = "; ".join(errors)
            yield rx.toast.error(
                f"Some deletion steps failed: {error_summary}. "
                "The platform remains in the list — you can retry deletion."
            )

    @rx.event(background=True)
    async def delete_platform_instant(self, instance_name: str):
        """Delete a platform from the overview table — backend-first with rollback on failure."""
        from ..thin_endpoint_wrappers import delete_platform, remove_from_inventory

        async with self:
            working_platform: Instance = self.platforms.get(instance_name)
            if working_platform is None:
                return

            platform_in_file = working_platform.platform.in_file
            host_id = working_platform.host.id
            display_name = working_platform.platform.config.instance_name

            # Show that we're working on it
            self._deleting_platform = True

        # --- Backend cleanup ---

        errors: list[str] = []

        if platform_in_file and instance_name:
            try:
                await delete_platform(instance_name)
                logger.info(f"Deleted platform backend data for {instance_name}")
            except Exception as e:
                logger.warning(f"Failed to delete platform files: {e}")
                errors.append(f"Platform data: {str(e)}")

            if host_id:
                try:
                    await remove_from_inventory(host_id)
                    logger.info(f"Deleted host entry for {instance_name}")
                except Exception as e:
                    logger.warning(f"Could not delete host entry: {e}")
                    errors.append(f"Host entry: {str(e)}")

        async with self:
            self._deleting_platform = False

            if not errors:
                # All backend calls succeeded — safe to remove from UI
                self.platforms = {k: v for k, v in self.platforms.items() if k != instance_name}
                # Clear stale current_uid so it doesn't point to deleted platform
                if self.current_uid == instance_name:
                    self.current_uid = ""

        if not errors:
            yield rx.toast.success(f"Platform {display_name} removed successfully")
        else:
            error_summary = "; ".join(errors)
            yield rx.toast.error(
                f"Some deletion steps failed: {error_summary}. "
                "The platform remains in the list — you can retry deletion."
            )

    # ---- Create platform dialog ----

    @rx.var
    def show_create_platform_dialog(self) -> bool:
        return self._show_create_platform_dialog

    @rx.var
    def connect_existing_mode(self) -> bool:
        return self._connect_existing_mode

    @rx.var
    def detecting_volttron(self) -> bool:
        return self._detecting_volttron

    @rx.var
    def detected_volttron_home(self) -> str:
        return self._detected_volttron_home

    @rx.var
    def detected_volttron_venv(self) -> str:
        return self._detected_volttron_venv

    @rx.var
    def detected_volttron_running(self) -> bool:
        return self._detected_volttron_running

    @rx.var
    def connect_ssh_host(self) -> str:
        return self._connect_ssh_host

    @rx.var
    def connect_ssh_user(self) -> str:
        return self._connect_ssh_user

    @rx.var
    def connect_ssh_port(self) -> str:
        return self._connect_ssh_port

    @rx.event
    def show_create_platform_options(self):
        """Show the create platform dialog with Deploy New / Connect Existing options"""
        self._show_create_platform_dialog = True
        self._connect_existing_mode = False
        self._detecting_volttron = False
        self._detected_volttron_home = ""
        self._detected_volttron_venv = ""
        self._detected_volttron_running = False
        self._connect_ssh_host = ""
        self._connect_ssh_user = ""
        self._connect_ssh_port = "22"

    @rx.event
    def close_create_platform_dialog(self):
        """Close the create platform dialog"""
        self._show_create_platform_dialog = False
        self._connect_existing_mode = False

    @rx.event
    async def generate_new_platform(self):
        """Create a new platform from scratch (deploy new)"""
        # Clean up any previously abandoned unsaved/temp platforms so they don't accumulate
        stale_uids = [uid for uid, inst in self.platforms.items()
                      if inst.new_instance and not inst.platform.in_file]
        if stale_uids:
            self.platforms = {k: v for k, v in self.platforms.items() if k not in stale_uids}

        new_uid = self.generate_unique_uid()
        # Use a unique default instance name so it never collides with existing platforms
        default_instance_name = f"volttron-{new_uid}"
        new_host = HostEntryModelView(id="", ansible_user="", ansible_host="")
        new_platform = PlatformModelView(
            config=PlatformConfigModelView(instance_name=default_instance_name),
            in_file=False,
        )
        new_platform.safe_platform = new_platform.to_dict()
        self.platforms[default_instance_name] = Instance(
                host=new_host,
                platform=new_platform,
                safe_host_entry=new_host.to_dict()
            )
        # Close the dialog if it's open
        self._show_create_platform_dialog = False
        self._connect_existing_mode = False
        # Route using the same key used in state to avoid UID/key drift.
        yield NavigationState.route_to_platform(default_instance_name)

    @rx.event
    def switch_to_connect_existing(self):
        """Switch to the 'Connect to Existing' flow"""
        self._connect_existing_mode = True

    @rx.event
    def switch_to_deploy_new(self):
        """Switch back to mode selection"""
        self._connect_existing_mode = False

    @rx.event
    def set_connect_ssh_host(self, value: str):
        self._connect_ssh_host = value

    @rx.event
    def set_connect_ssh_user(self, value: str):
        self._connect_ssh_user = value

    @rx.event
    def set_connect_ssh_port(self, value: str):
        self._connect_ssh_port = value

    @rx.event(background=True)
    async def detect_existing_volttron(self):
        """Detect existing VOLTTRON installation on remote machine"""
        async with self:
            if not self._connect_ssh_host or not self._connect_ssh_user:
                yield rx.toast.error("Please enter SSH host and user")
                return

            self._detecting_volttron = True
            ssh_host = self._connect_ssh_host
            ssh_user = self._connect_ssh_user
            ssh_port = self._connect_ssh_port or "22"

        yield

        try:
            result = await detect_existing_volttron(ssh_host, ssh_user, ssh_port)

            async with self:
                self._detecting_volttron = False
                self._detected_volttron_home = result.get("volttron_home", "~/.volttron")
                self._detected_volttron_venv = result.get("volttron_venv", "~/volttron.venv")
                self._detected_volttron_running = result.get("is_running", False)

            if result.get("is_running"):
                yield rx.toast.success("Found running VOLTTRON instance!")
            elif result.get("volttron_found"):
                yield rx.toast.info("Found VOLTTRON installation (not currently running)")
            else:
                yield rx.toast.warning("Could not detect VOLTTRON - using default paths")

        except ApiError as e:
            async with self:
                self._detecting_volttron = False
            yield rx.toast.error(f"Detection failed: {e.detail}")
        except Exception as e:
            async with self:
                self._detecting_volttron = False
            yield rx.toast.error(f"Error: {str(e)}")

    # ---- Password deploy dialog ----

    @rx.var
    def needs_password_for_deployment(self) -> bool:
        """Check if current platform needs a password for deployment"""
        if self.current_uid not in self.platforms:
            return False

        working_platform = self.platforms[self.current_uid]

        # Local connections don't need passwords
        if working_platform.host.ansible_connection == "local":
            return False

        # SSH connections need password if not already provided
        # (assumes key-based auth if password is not set)
        return working_platform.password == ""

    @rx.event
    def update_password_field(self, value: str):
        uid = self.current_uid
        logger.debug(f"[PWD_DIALOG] update_password_field called, uid={uid!r}, _show_password_dialog={self.show_password_dialog}")
        if uid not in self.platforms:
            uid = next(
                (k for k, v in self.platforms.items()
                 if v.platform.config.instance_name == self.current_uid),
                "",
            )
        if uid == "" or uid not in self.platforms:
            logger.debug(f"[PWD_DIALOG] update_password_field ABORT: uid={uid!r} not found")
            return
        working_platform_instance = self.platforms[uid]
        working_platform_instance.password = value
        logger.debug(f"[PWD_DIALOG] password updated, _show_password_dialog still={self.show_password_dialog}")

    @rx.event
    def open_password_deploy_dialog(self):
        logger.debug(f"[PWD_DIALOG] open_password_deploy_dialog called, current_uid={self.current_uid!r}, in_platforms={self.current_uid in self.platforms}")
        if self.current_uid not in self.platforms:
            logger.debug("[PWD_DIALOG] ABORT: current_uid not in platforms")
            return
        self.deploy_password_error = ""
        self.show_password_dialog = True
        logger.debug(f"[PWD_DIALOG] _show_password_dialog set to True")

    @rx.event
    def close_password_deploy_dialog(self):
        logger.debug(f"[PWD_DIALOG] close_password_deploy_dialog called")
        if self.current_uid in self.platforms:
            self.platforms[self.current_uid].password = ""
        self.checking_deploy_connection = False
        self.deploy_password_error = ""
        self.show_password_dialog = False
        logger.debug(f"[PWD_DIALOG] _show_password_dialog set to False")

    @rx.event
    def handle_cancel(self):
        """Revert unsaved changes on the current platform."""
        from ..model_views import HostEntryModelView
        if self.current_uid not in self.platforms:
            return
        working_platform: Instance = self.platforms[self.current_uid]

        # Reset deploy password flow UI state.
        self.checking_deploy_connection = False
        self.deploy_password_error = ""
        self.show_password_dialog = False

        # Revert back to our previous host entry
        working_platform.host = HostEntryModelView(**working_platform.safe_host_entry)
        working_platform.uncaught = False
        working_platform.valid = working_platform.does_host_have_errors()

        # Revert back to our previous platform
        working_platform.platform.config.instance_name = working_platform.platform.safe_platform["config"].get("instance_name", "volttron1")
        working_platform.platform.config.vip_address = working_platform.platform.safe_platform["config"].get("vip_address", "tcp://127.0.0.1:22916")

        # Revert our platform's agents
        for agent in working_platform.platform.agents.values():
            if agent.is_new:
                del(working_platform.platform.agents[agent.identity])

        logger.debug("i pressed cancel,")
        yield rx.toast.info("Changes Reverted.")

    # Note: show_remove_agent_dialog, agent_to_remove_name, agent_to_remove_uuid,
    # show_install_agent_dialog, install_agent_mode, selected_catalog_agent,
    # selected_local_agent, install_agent_identity, install_agent_source,
    # install_agent_start, installing_agent, has_github_agents, has_local_agents
    # are all inherited from PlatformAgentState (via the inheritance chain).
    # We also need show_remove_agent_dialog / agent_to_remove_* getters here
    # since the private vars are defined in PlatformAgentState but those getters
    # were in the original state.py's PlatformPageState scope.

    @rx.var
    def show_remove_agent_dialog(self) -> bool:
        return self._show_remove_agent_dialog

    @rx.var
    def agent_to_remove_name(self) -> str:
        return self._agent_to_remove_name

    @rx.var
    def agent_to_remove_uuid(self) -> str:
        return self._agent_to_remove_uuid

    @rx.var
    def has_github_agents(self) -> bool:
        return len(self.github_agents) > 0

    @rx.var
    def has_local_agents(self) -> bool:
        return len(self.local_agents) > 0