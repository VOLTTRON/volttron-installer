"""PlatformSaveState - Save, update, toggle, and connect-to-existing platform operations."""

import reflex as rx
import json
import re
from loguru import logger
from copy import deepcopy

from ..models import Instance
from ..model_views import HostEntryModelView, PlatformModelView, PlatformConfigModelView
from ..backend.models import AgentType, HostEntry, PlatformConfig, PlatformDefinition, ConfigStoreEntry, AgentDefinition, CreatePlatformRequest, CreateOrUpdateHostEntryRequest
from ..thin_endpoint_wrappers import get_all_platforms, update_platform, create_platform, add_host, check_platform_connection, mark_platform_deployed, ApiError
from ..navigation.state import NavigationState

from .platform_dialogs import PlatformDialogState


class PlatformSaveState(PlatformDialogState):
    @rx.event
    def toggle_advanced(self):
        if self.current_uid not in self.platforms:
            return
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.advanced_expanded = not working_platform.advanced_expanded

    @rx.event
    def toggle_agent_config_details(self):
        if self.current_uid not in self.platforms:
            return
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.agent_configuration_expanded = not working_platform.agent_configuration_expanded

    @rx.event
    def toggle_web(self):
        if self.current_uid not in self.platforms:
            return
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.web_checked = not working_platform.web_checked

    @rx.event
    def toggle_federation(self):
        if self.current_uid not in self.platforms:
            return
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.federation_checked = not working_platform.federation_checked

    @rx.event
    def update_detail(self, field: str, value):
        uid = self.current_uid
        if uid not in self.platforms:
            uid = next(
                (k for k, v in self.platforms.items()
                 if v.platform.config.instance_name == self.current_uid),
                "",
            )
        if uid == "" or uid not in self.platforms:
            return
        logger.info(f"[HOST UPDATE] Updating {field} to: '{value}'")
        working_platform_instance = self.platforms[uid]
        if field == "id":
            self._host_resolved = False
            setattr(working_platform_instance.host, "ansible_host", value)
        setattr(working_platform_instance.host, field, value)
        logger.info(f"[HOST UPDATE] After update, {field} = '{getattr(working_platform_instance.host, field)}'")
        working_platform_instance.uncaught = working_platform_instance.has_uncaught_changes()

    @rx.event
    def update_platform_config_detail(self, field: str, value: str):
        if self.current_uid not in self.platforms:
            return
        logger.info(f"[CONFIG UPDATE] Updating {field} to: '{value}'")
        working_platform = self.platforms[self.current_uid]
        if field == "web_bind_address":
            setattr(working_platform, field, value)
        else:
            setattr(working_platform.platform.config, field, value)
        # Log the current value after update
        if field == "volttron_version":
            logger.info(f"[CONFIG UPDATE] After update, volttron_version = '{working_platform.platform.config.volttron_version}'")

    @rx.event
    def use_local_details(self):
        uid = self.current_uid
        if uid not in self.platforms:
            uid = next(
                (k for k, v in self.platforms.items()
                 if v.platform.config.instance_name == self.current_uid),
                "",
            )
        if uid == "" or uid not in self.platforms:
            yield rx.toast.error("Active platform not found. Please reopen the instance from Instances.")
            return
        import getpass
        current_user = getpass.getuser()

        # Get the current platform instance
        working_platform = self.platforms[uid]

        # Update Host Entry details for localhost
        working_platform.host.ansible_host = "localhost"
        working_platform.host.id = "localhost"
        working_platform.host.ansible_user = current_user
        working_platform.host.ansible_port = "22"
        working_platform.host.ansible_connection = "local"  # Set to local connection - no SSH needed

        # No password needed for local connections
        working_platform.password = ""

        # Update validation states since we trust localhost
        self._host_resolved = True
        self._host_resolvable = True

        # Check for uncaught changes
        working_platform.uncaught = working_platform.has_uncaught_changes()

        # Reassign dict to guarantee Reflex notices nested model mutations.
        self.platforms = dict(self.platforms)

        yield rx.toast.info("Configured for local connection (no SSH or password needed)")

    @rx.event
    async def connect_to_existing_platform(self):
        """Create a platform entry for an existing VOLTTRON installation"""
        from ..model_views import HostEntryModelView
        if not self._connect_ssh_host or not self._connect_ssh_user:
            yield rx.toast.error("Please enter SSH host and user")
            return

        # Use the SSH host as the instance name for clarity
        # Replace dots with hyphens to pass validation (e.g., 192.168.1.248 -> 192-168-1-248)
        instance_name = self._connect_ssh_host.replace(".", "-")

        # Use detected paths or defaults
        volttron_home = self._detected_volttron_home or "~/.volttron"
        volttron_venv = self._detected_volttron_venv or "~/volttron.venv"

        # Create host entry with SSH details
        new_host = HostEntryModelView(
            id=self._connect_ssh_host,
            ansible_user=self._connect_ssh_user,
            ansible_host=self._connect_ssh_host,
            ansible_port=self._connect_ssh_port or "22",
            volttron_home=volttron_home,
            volttron_venv=volttron_venv
        )

        # Create platform - mark as deployed since it already exists
        # in_file=True enables Status and Logs tabs
        new_platform = PlatformModelView(
            config=PlatformConfigModelView(instance_name=instance_name),
            in_file=True
        )
        new_platform.safe_platform = new_platform.to_dict()

        instance = Instance(
            host=new_host,
            platform=new_platform,
            safe_host_entry=new_host.to_dict(),
            new_instance=False,  # Not a new instance - already exists
            deployed=True,  # Mark as already deployed
        )

        # Save to backend so Status tab can fetch platform info
        try:
            # Save the host entry
            host_request = new_host.to_dict()
            host_request["ansible_port"] = int(host_request["ansible_port"])
            host_request["instance_name"] = instance_name
            await add_host(CreateOrUpdateHostEntryRequest(**host_request))

            # Save the platform
            platform_request = CreatePlatformRequest(
                host_id=new_host.id,
                config=PlatformConfig(
                    instance_name=instance_name,
                    vip_address="tcp://127.0.0.1:22916"  # Default VIP
                ),
                agents={}
            )
            await create_platform(platform_request)
        except Exception as e:
            logger.error(f"Error saving platform to backend: {e}")
            yield rx.toast.error(f"Error saving platform: {e}")
            return

        self.platforms[instance_name] = instance

        # Close dialog and navigate
        self._show_create_platform_dialog = False
        self._connect_existing_mode = False

        # Set loading states before navigating so UI shows "Checking..." immediately
        self._status_loading = True
        self._connection_status = "checking"

        self.current_uid = instance_name
        yield NavigationState.route_to_platform(instance_name)
        yield rx.toast.success("Connected to existing VOLTTRON instance!")

    @rx.event
    async def handle_save(self):
        """Save platform configuration and immediately start deployment"""
        from .platform_deployment import PlatformDeploymentState

        if self.current_uid not in self.platforms:
            yield rx.toast.error("No platform selected")
            return
        working_platform: Instance = self.platforms[self.current_uid]
        uid_copy = deepcopy(self.current_uid)
        is_remote_connection = working_platform.host.ansible_connection != "local"

        if is_remote_connection and working_platform.password == "":
            self.deploy_password_error = "Please enter your SSH password to continue deployment."
            self.show_password_dialog = True
            return

        if is_remote_connection:
            self.checking_deploy_connection = True
            self.deploy_password_error = ""
            yield

        logger.debug(f"this is the uid copy: {uid_copy}")
        all_platforms: list[PlatformDefinition] = await get_all_platforms()
        api_instance_names = [p.config.instance_name for p in all_platforms]

        working_platform.safe_host_entry = working_platform.host.to_dict()
        working_platform.uncaught = False

        # Create base platform request with deployed=True since we're about to deploy
        base_platform_request = CreatePlatformRequest(
            host_id = working_platform.safe_host_entry["id"],
            config=PlatformConfig(
                instance_name=working_platform.platform.config.instance_name,
                vip_address=working_platform.platform.config.vip_address,
                message_bus=working_platform.platform.config.message_bus,
                volttron_type=working_platform.platform.config.volttron_type,
                volttron_version=working_platform.platform.config.volttron_version,
            ),
            agents = {
                identity: AgentDefinition(
                    identity=identity,
                    source=agent["source"],
                    config=agent["config"],
                    config_store_allowed=agent["config_store_allowed"],
                    config_store={
                        path: ConfigStoreEntry(
                            path=path,
                            data_type=config["data_type"],
                            value=config["value"]
                        ) for path, config in agent["config_store"].items()
                    }
                ) for identity, agent in working_platform.platform.to_dict()["agents"].items()
            },
            deployed=True
        )

        desired_name = working_platform.platform.config.instance_name

        # Determine whether we are editing an existing saved platform (uid_copy is a known
        # instance name in the API) or creating a brand-new one (uid_copy is a temp random id).
        is_existing_platform = uid_copy in api_instance_names

        try:
            if is_existing_platform:
                # ── Editing an already-saved platform ────────────────────────────
                logger.debug(f"Updating existing platform {uid_copy!r} (desired name: {desired_name!r})")
                await update_platform(uid_copy, base_platform_request)
                # If the instance was renamed the old key still lives in api; keep memory key aligned
                if uid_copy != desired_name:
                    self.platforms[desired_name] = self.platforms.pop(uid_copy, working_platform)
            else:
                # ── Creating a new platform ──────────────────────────────────────
                # Guard: if the desired instance name is taken by a *different* platform, refuse.
                if desired_name in api_instance_names:
                    yield rx.toast.error(
                        f"An instance named '{desired_name}' already exists. "
                        "Please choose a different name before saving."
                    )
                    return

                host_request = working_platform.host.to_dict()
                host_request["ansible_port"] = int(host_request["ansible_port"])
                host_request["instance_name"] = desired_name
                logger.info(f"[SAVE] Host request volttron_home: '{host_request.get('volttron_home')}'")
                logger.info(f"[SAVE] Host request volttron_venv: '{host_request.get('volttron_venv')}'")
                request = CreateOrUpdateHostEntryRequest(**host_request)
                await add_host(request)
                await create_platform(base_platform_request)

                # Register the platform under its proper instance-name key
                self.platforms[desired_name] = working_platform
                logger.debug(f"Platform created, platforms now: {list(self.platforms.keys())}")
        except ApiError as e:
            self.checking_deploy_connection = False
            self.deploy_password_error = ""
            self.show_password_dialog = False

            message = e.detail
            try:
                parsed = json.loads(e.detail)
                if isinstance(parsed, dict) and parsed.get("detail"):
                    message = parsed["detail"]
            except Exception:
                pass

            # If VIP collides on same host, auto-suggest the next port and let user retry.
            if e.status_code == 409 and "VIP port collision" in message:
                current_vip = working_platform.platform.config.vip_address
                host_match = re.match(r"^tcp://([^:]+):(\d+)$", current_vip)
                vip_host = host_match.group(1) if host_match else "127.0.0.1"
                used_ports = set()
                for p in all_platforms:
                    m = re.match(r"^tcp://[^:]+:(\d+)$", p.config.vip_address)
                    if m:
                        used_ports.add(int(m.group(1)))
                next_port = 22916
                while next_port in used_ports:
                    next_port += 1
                working_platform.platform.config.vip_address = f"tcp://{vip_host}:{next_port}"
                working_platform.uncaught = True
                yield rx.toast.error(
                    f"{message} Suggested VIP updated to tcp://{vip_host}:{next_port}. "
                    "Click Save & Deploy again."
                )
                return

            yield rx.toast.error(f"Save failed: {message}")
            return

        # Always clean up the temp random-UID entry so it never leaks
        if uid_copy != desired_name and uid_copy in self.platforms:
            yield PlatformSaveState.delete_temp_uid(uid_copy)

        # Legacy cleanup: older flows created temp keys like "AbC123x" while
        # instance_name was "volttron-AbC123x". Remove that orphan key if present.
        legacy_uid = ""
        if desired_name.startswith("volttron-"):
            legacy_uid = desired_name.removeprefix("volttron-")
        if legacy_uid and legacy_uid in self.platforms and legacy_uid != desired_name:
            yield PlatformSaveState.delete_temp_uid(legacy_uid)

        # Preflight check for remote deployments: verify SSH access BEFORE running deploy.
        # This avoids deep ansible failures when keys/password auth are not configured.
        if working_platform.host.ansible_connection != "local":
            connection_ok = False
            connection_error = ""
            check_ids = []
            if desired_name:
                check_ids.append(desired_name)
            if uid_copy and uid_copy != desired_name:
                check_ids.append(uid_copy)

            for platform_id in check_ids:
                try:
                    result = await check_platform_connection(platform_id)
                    if result.get("connected", False):
                        connection_ok = True
                        break
                    connection_error = result.get("error", "SSH connection failed")
                except Exception as conn_exc:
                    connection_error = str(conn_exc)

            if not connection_ok:
                error_lower = (connection_error or "").lower()
                if "permission denied" in error_lower or "publickey" in error_lower:
                    ssh_user = working_platform.host.ansible_user
                    ssh_host = working_platform.host.ansible_host
                    ssh_port = working_platform.host.ansible_port
                    friendly = (
                        "Cannot deploy yet: SSH authentication is not set up for this host. "
                        f"Set up key-based SSH access (recommended) with `ssh-copy-id -p {ssh_port} {ssh_user}@{ssh_host}`, "
                        "or verify the username/password and host SSH settings, then try again."
                    )
                elif "host key verification failed" in error_lower or "authenticity" in error_lower:
                    friendly = (
                        "Cannot deploy yet: SSH host key is not trusted. "
                        "SSH to the host once manually and accept the key, then retry deployment."
                    )
                else:
                    friendly = f"Cannot deploy yet: SSH preflight failed ({connection_error})."

                # Platform remains saved, but deployment is blocked until connectivity is fixed.
                working_platform.deployed = False
                working_platform.platform.in_file = True
                working_platform.new_instance = False
                working_platform.platform.safe_platform = working_platform.platform.to_dict()
                self.checking_deploy_connection = False
                self.deploy_password_error = friendly
                self.show_password_dialog = True
                # Force a fresh re-entry after failed auth/preflight.
                working_platform.password = ""
                try:
                    await mark_platform_deployed(desired_name, False)
                except Exception:
                    pass

                yield rx.toast.error(friendly)
                return

        self.checking_deploy_connection = False
        self.deploy_password_error = ""
        self.show_password_dialog = False

        yield rx.toast.success("Configuration saved, starting deployment...")

        # Mark platform as deployed in memory and enable tabs BEFORE navigating
        working_platform.deployed = True
        working_platform.platform.in_file = True
        working_platform.new_instance = False
        working_platform.platform.safe_platform = working_platform.platform.to_dict()

        # Navigate to the instance and trigger deployment
        yield NavigationState.route_to_platform(desired_name)
        yield PlatformDeploymentState.handle_deploy()