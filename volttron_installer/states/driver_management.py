"""
Driver Management State - Handles CRUD operations for platform drivers.

Platform drivers are configurations loaded by the platform.driver agent.
Each driver consists of:
- Registry CSV: Defines device data points
- Device Config JSON: Specifies driver type, location, registry reference
"""

import reflex as rx
import json
import re
from typing import Optional
from loguru import logger

from .platform_deployment import PlatformDeploymentState
from ..model_views import AgentModelView, ConfigStoreEntryModelView
from ..utils.create_component_uid import generate_unique_uid


async def _save_platform_config(platform_instance, current_uid: str):
    """Save platform config to the backend API.

    Builds a CreatePlatformRequest from the working platform state and calls
    update_platform. This is the correct way to persist config changes —
    it mirrors the serialization in PlatformPageState.handle_save.
    """
    from ..thin_endpoint_wrappers import update_platform
    from ..backend.models import (
        CreatePlatformRequest,
        PlatformConfig,
        AgentDefinition,
        ConfigStoreEntry,
    )

    request = CreatePlatformRequest(
        host_id=platform_instance.safe_host_entry.get("id", current_uid),
        config=PlatformConfig(
            instance_name=platform_instance.platform.config.instance_name,
            vip_address=platform_instance.platform.config.vip_address,
            message_bus=platform_instance.platform.config.message_bus,
            volttron_type=platform_instance.platform.config.volttron_type,
            volttron_version=platform_instance.platform.config.volttron_version,
        ),
        agents={
            identity: AgentDefinition(
                identity=identity,
                source=agent["source"],
                config=agent["config"],
                config_store_allowed=agent.get("config_store_allowed", True),
                config_store={
                    path: ConfigStoreEntry(
                        path=path,
                        data_type=cfg["data_type"],
                        value=cfg["value"],
                    )
                    for path, cfg in agent["config_store"].items()
                },
            )
            for identity, agent in platform_instance.platform.to_dict()["agents"].items()
        },
        deployed=platform_instance.deployed,
    )
    await update_platform(current_uid, request)


class DriverManagementState(PlatformDeploymentState):
    """State for managing platform driver configurations"""
    
    # Dialog visibility
    _show_add_driver_dialog: bool = False
    _show_edit_driver_dialog: bool = False
    _show_delete_driver_dialog: bool = False
    _show_deploy_drivers_dialog: bool = False
    _show_install_driver_lib_dialog: bool = False
    _show_configure_driver_dialog: bool = False
    
    # Configure driver from installed lib
    _configure_driver_name: str = ""  # Display name of driver being configured
    _configure_step: int = 1            # 1 = device JSON editor, 2 = CSV editor
    _configure_device_name: str = ""    # key name for the device JSON entry
    _configure_device_json: str = "{}"  # raw JSON text for step 1
    _configure_csv_name: str = ""       # key name for the registry CSV entry
    _configure_csv_content: str = ""    # raw CSV text for step 2
    _configure_driver_type: str = ""    # driver_type for current wizard
    _configure_required_agents: list[str] = []
    _configure_driver_config_fields: list[dict[str, str | bool]] = []
    _configure_driver_config_values: dict[str, str | bool] = {}
    
    # Driver form fields
    _driver_type: str = "fake"
    _campus: str = "campus"
    _building: str = "building"
    _unit: str = "fake"
    _interval: int = 5
    _timezone: str = "US/Pacific"
    _heart_beat_point: str = "Heartbeat"
    _registry_config_name: str = ""  # Selected existing registry
    _new_registry_name: str = ""  # Name for new registry
    _new_registry_content: str = ""  # Content for new registry
    _driver_config_json: str = "{}"  # Advanced driver_config
    
    # Driver library install fields
    _selected_driver_lib: str = ""  # pip package name of selected catalog driver
    _custom_driver_lib: str = ""  # custom pip package name entered by user
    _install_driver_lib_mode: str = "catalog"  # "catalog", "local", or "manual"
    _selected_local_driver_lib: str = ""  # local path selected from local workspace
    _local_driver_libs: list[dict[str, str]] = []  # [{name, path, description}]
    _loading_local_driver_libs: bool = False
    _installing_driver_lib: bool = False
    _driver_lib_install_result: str = ""
    
    # Installed driver libraries (from pip list)
    _installed_driver_libs: list[dict[str, str]] = []  # [{"name": ..., "version": ...}]
    _loading_installed_drivers: bool = False

    # vctl config list state
    _vctl_config_agents: list[str] = []         # all agents with config store entries
    _agent_config_keys: dict[str, list[str]] = {}  # keys per agent
    _expanded_agents: dict[str, bool] = {}      # which agents are expanded
    _vctl_agents_loading: bool = False          # loading the top-level agent list
    _vctl_keys_loading: str = ""               # agent whose keys are currently loading

    # Live config key editing
    _live_editing_agent: str = ""               # agent for the current edit/delete op
    _live_editing_key: str = ""                 # key being edited/deleted via vctl
    _show_delete_live_config_dialog: bool = False
    _live_key_loading: bool = False

    # Simple live config editor
    _show_live_edit_dialog: bool = False
    _live_edit_content: str = ""
    _live_edit_saving: bool = False

    # Editing state
    _editing_driver_path: str = ""  # Path of driver being edited
    _editing_driver_config_id: str = ""  # Config ID being edited
    _editing_registry_id: str = ""  # Registry ID being edited
    
    # Loading states
    _loading_drivers: bool = False
    _deploying_configs: bool = False
    
    # Validation
    _form_errors: dict[str, str] = {}

    @rx.var
    def installed_driver_libs(self) -> list[dict[str, str]]:
        """List of installed driver library packages [{name, version}]."""
        return self._installed_driver_libs

    @rx.var
    def loading_installed_drivers(self) -> bool:
        return self._loading_installed_drivers

    @rx.var
    def installed_driver_names(self) -> list[str]:
        """Lowercase pip package names of installed drivers for quick lookup."""
        return [d.get("name", "").lower() for d in self._installed_driver_libs]

    @rx.var
    def driver_library_catalog(self) -> list[dict]:
        """Return the hardcoded driver library catalog as dicts for the UI."""
        from ..backend.models import DriverLibraryCatalog
        catalog = DriverLibraryCatalog()
        return [d.model_dump() for d in catalog.drivers]

    @rx.var
    def driver_type_options(self) -> list[str]:
        """Unique driver_type values from the driver library catalog."""
        from ..backend.models import DriverLibraryCatalog
        catalog = DriverLibraryCatalog()
        seen: set[str] = set()
        options: list[str] = []
        for entry in catalog.drivers:
            dtype = entry.driver_type.strip()
            if dtype and dtype not in seen:
                seen.add(dtype)
                options.append(dtype)
        if "fake" not in seen:
            options.insert(0, "fake")
        return options

    @rx.var
    def driver_lib_to_install(self) -> str:
        """The pip package that will be installed — either catalog selection or custom."""
        if self._install_driver_lib_mode == "catalog":
            return self._selected_driver_lib
        if self._install_driver_lib_mode == "local":
            return self._selected_local_driver_lib.strip()
        if self._custom_driver_lib.strip():
            return self._custom_driver_lib.strip()
        return ""

    @rx.var
    def install_driver_lib_mode(self) -> str:
        return self._install_driver_lib_mode

    @rx.var
    def selected_local_driver_lib(self) -> str:
        return self._selected_local_driver_lib

    @rx.var
    def local_driver_libs(self) -> list[dict[str, str]]:
        return self._local_driver_libs

    @rx.var
    def loading_local_driver_libs(self) -> bool:
        return self._loading_local_driver_libs

    @rx.var
    def has_local_driver_libs(self) -> bool:
        return len(self._local_driver_libs) > 0

    # Expose private vars as public computed properties for UI binding
    @rx.var
    def driver_type(self) -> str:
        return self._driver_type

    @rx.var
    def campus(self) -> str:
        return self._campus

    @rx.var
    def building(self) -> str:
        return self._building

    @rx.var
    def unit(self) -> str:
        return self._unit

    @rx.var
    def interval(self) -> int:
        return self._interval

    @rx.var
    def timezone(self) -> str:
        return self._timezone

    @rx.var
    def heart_beat_point(self) -> str:
        return self._heart_beat_point

    @rx.var
    def driver_config_json(self) -> str:
        return self._driver_config_json

    @rx.var
    def registry_config_name(self) -> str:
        return self._registry_config_name

    @rx.var
    def new_registry_name(self) -> str:
        return self._new_registry_name

    @rx.var
    def new_registry_content(self) -> str:
        return self._new_registry_content

    @rx.var
    def show_add_driver_dialog(self) -> bool:
        return self._show_add_driver_dialog

    @rx.var
    def show_edit_driver_dialog(self) -> bool:
        return self._show_edit_driver_dialog

    @rx.var
    def show_delete_driver_dialog(self) -> bool:
        return self._show_delete_driver_dialog

    @rx.var
    def show_install_driver_lib_dialog(self) -> bool:
        return self._show_install_driver_lib_dialog

    @rx.var
    def show_configure_driver_dialog(self) -> bool:
        return self._show_configure_driver_dialog

    @rx.var
    def selected_driver_lib(self) -> str:
        return self._selected_driver_lib

    @rx.var
    def custom_driver_lib(self) -> str:
        return self._custom_driver_lib

    @rx.var
    def driver_lib_install_result(self) -> str:
        return self._driver_lib_install_result

    @rx.var
    def installing_driver_lib(self) -> bool:
        return self._installing_driver_lib

    @rx.var
    def configure_driver_name(self) -> str:
        return self._configure_driver_name

    @rx.var
    def deploying_configs(self) -> bool:
        return self._deploying_configs

    @rx.var
    def can_install_driver_lib(self) -> bool:
        if self._install_driver_lib_mode == "catalog":
            return self._selected_driver_lib.strip() != ""
        if self._install_driver_lib_mode == "local":
            return self._selected_local_driver_lib.strip() != ""
        return self._custom_driver_lib.strip() != ""

    @rx.var
    def platform_driver_agent(self) -> Optional[AgentModelView]:
        """Get platform.driver agent from current platform"""
        if not self.current_uid or self.current_uid not in self.platforms:
            return None
        platform = self.platforms[self.current_uid]
        return platform.platform.agents.get("platform.driver")

    @rx.var
    def platform_driver_exists(self) -> bool:
        """Check if platform.driver agent is configured in saved config or running live."""
        if self.platform_driver_agent is not None:
            return True
        # Also accept it when the live VOLTTRON instance reports it as running.
        # vctl uses "platform-driver" (hyphen) as the VIP identity key,
        # while the saved config uses "platform.driver" (dot). Check both.
        return "platform.driver" in self.platform_agents or "platform-driver" in self.platform_agents

    @rx.var
    def driver_configs(self) -> list[dict]:
        """Parse platform.driver config_store into list of drivers"""
        agent = self.platform_driver_agent
        if not agent:
            return []
        
        drivers = []
        for config in agent.config_store:
            # Device configs are JSON files in devices/ path
            if config.path.startswith("devices/") and config.data_type == "JSON":
                try:
                    device_config = json.loads(config.value)
                    
                    # Parse path: devices/campus/building/unit
                    path_parts = config.path.split("/")
                    campus = path_parts[1] if len(path_parts) > 1 else "unknown"
                    building = path_parts[2] if len(path_parts) > 2 else "unknown"
                    unit = path_parts[3] if len(path_parts) > 3 else "unknown"
                    
                    # Get registry reference
                    registry_config = device_config.get("registry_config", "")
                    registry_name = registry_config.replace("config://", "")
                    
                    drivers.append({
                        "path": config.path,
                        "campus": campus,
                        "building": building,
                        "unit": unit,
                        "driver_type": device_config.get("driver_type", "unknown"),
                        "registry": registry_name,
                        "interval": device_config.get("interval", 5),
                        "timezone": device_config.get("timezone", "US/Pacific"),
                        "config_id": config.component_id,
                        "driver_config": device_config.get("driver_config", {}),
                        "heart_beat_point": device_config.get("heart_beat_point", ""),
                    })
                except (json.JSONDecodeError, IndexError, KeyError) as e:
                    logger.warning(f"Failed to parse driver config {config.path}: {e}")
                    continue
        
        return sorted(drivers, key=lambda x: f"{x['campus']}/{x['building']}/{x['unit']}")

    @rx.var
    def drivers_count(self) -> int:
        """Count of configured drivers"""
        return len(self.driver_configs)

    @rx.var
    def available_registries(self) -> list[str]:
        """Get list of available registry CSV files from config_store"""
        agent = self.platform_driver_agent
        if not agent:
            return []
        
        registries = []
        for config in agent.config_store:
            if config.data_type == "CSV" and not config.path.startswith("devices/"):
                registries.append(config.path)
        
        return sorted(registries)

    @rx.var
    def available_registries_with_empty(self) -> list[str]:
        """Get list of available registries with empty option for select"""
        return [""] + self.available_registries

    @rx.var
    def can_add_driver(self) -> bool:
        """Validate if driver can be added"""
        if not self._campus or not self._building or not self._unit:
            return False
        if not self._driver_type:
            return False
        # Must have either selected existing registry or provided new one
        if not self._registry_config_name and not (self._new_registry_name and self._new_registry_content):
            return False
        return True

    @rx.var
    def driver_path(self) -> str:
        """Generate device config path from form fields"""
        return f"devices/{self._campus}/{self._building}/{self._unit}"

    @rx.event
    async def on_drivers_tab_mount(self):
        """Called when the Drivers tab is mounted — fires both fetch events."""
        yield DriverManagementState.fetch_installed_driver_libs
        yield DriverManagementState.fetch_vctl_config_list

    # Fetch installed driver libraries
    @rx.event
    async def fetch_installed_driver_libs(self):
        """Query the VOLTTRON venv for currently installed driver libraries."""
        if not self.current_uid:
            return
        self._loading_installed_drivers = True
        yield
        try:
            from ..thin_endpoint_wrappers import get_installed_driver_libraries
            response = await get_installed_driver_libraries(self.current_uid)
            if response.status_code == 200:
                data = response.json()
                self._installed_driver_libs = data.get("installed_drivers", [])
            else:
                logger.warning(f"Failed to fetch installed drivers: {response.text}")
                self._installed_driver_libs = []
        except Exception as e:
            logger.error(f"Error fetching installed driver libraries: {e}")
            self._installed_driver_libs = []
        finally:
            self._loading_installed_drivers = False
            yield

    # vctl config list computed vars
    @rx.var
    def vctl_config_agents(self) -> list[str]:
        return self._vctl_config_agents

    @rx.var
    def vctl_agents_loading(self) -> bool:
        return self._vctl_agents_loading

    @rx.var
    def vctl_keys_loading(self) -> str:
        return self._vctl_keys_loading

    @rx.var
    def config_tree_rows(self) -> list[dict]:
        """Flat list of rows for the config store tree UI.
        Each row is {type, agent, key, expanded, loading}.
        """
        rows: list[dict] = []
        for agent in self._vctl_config_agents:
            expanded = self._expanded_agents.get(agent, False)
            loading = self._vctl_keys_loading == agent
            rows.append({
                "type": "agent",
                "agent": agent,
                "key": "",
                "expanded": expanded,
                "loading": loading,
            })
            if expanded:
                for key in self._agent_config_keys.get(agent, []):
                    rows.append({
                        "type": "key",
                        "agent": agent,
                        "key": key,
                        "expanded": False,
                        "loading": False,
                    })
        return rows

    @rx.event
    async def fetch_vctl_config_list(self):
        """Run vctl config list to get all agents with config store entries."""
        if not self.current_uid:
            return
        self._vctl_agents_loading = True
        yield
        try:
            from ..thin_endpoint_wrappers import get_vctl_config_list
            response = await get_vctl_config_list(self.current_uid)
            data = response.json() if hasattr(response, "json") else response
            self._vctl_config_agents = data.get("entries", [])
            # Refresh keys for any agent that is currently expanded
            for agent in list(self._expanded_agents.keys()):
                if self._expanded_agents.get(agent) and agent in self._vctl_config_agents:
                    yield DriverManagementState.fetch_agent_config_keys(agent)
        except Exception as e:
            logger.error(f"Error running vctl config list: {e}")
        finally:
            self._vctl_agents_loading = False
            yield

    @rx.event
    async def fetch_agent_config_keys(self, agent: str):
        """Run vctl config list <agent> to get its config keys."""
        if not self.current_uid or not agent:
            return
        self._vctl_keys_loading = agent
        yield
        try:
            from ..thin_endpoint_wrappers import get_vctl_config_list
            response = await get_vctl_config_list(self.current_uid, agent)
            data = response.json() if hasattr(response, "json") else response
            self._agent_config_keys[agent] = data.get("entries", [])
        except Exception as e:
            logger.error(f"Error running vctl config list {agent}: {e}")
            self._agent_config_keys[agent] = []
        finally:
            if self._vctl_keys_loading == agent:
                self._vctl_keys_loading = ""
            yield

    @rx.var
    def live_editing_agent(self) -> str:
        return self._live_editing_agent

    @rx.var
    def live_editing_key(self) -> str:
        return self._live_editing_key

    @rx.var
    def show_delete_live_config_dialog(self) -> bool:
        return self._show_delete_live_config_dialog

    @rx.var
    def live_key_loading(self) -> bool:
        return self._live_key_loading

    @rx.var
    def configure_step(self) -> int:
        return self._configure_step

    @rx.var
    def configure_device_name(self) -> str:
        return self._configure_device_name

    @rx.var
    def configure_device_json(self) -> str:
        return self._configure_device_json

    @rx.var
    def configure_csv_name(self) -> str:
        return self._configure_csv_name

    @rx.var
    def configure_csv_content(self) -> str:
        return self._configure_csv_content

    @rx.var
    def configure_driver_type(self) -> str:
        return self._configure_driver_type

    @rx.var
    def configure_required_agents(self) -> list[str]:
        return self._configure_required_agents

    @rx.var
    def configure_driver_config_fields(self) -> list[dict[str, str | bool]]:
        return self._configure_driver_config_fields

    @rx.var
    def configure_driver_config_values(self) -> dict[str, str | bool]:
        return self._configure_driver_config_values

    @rx.var
    def configure_has_field_form(self) -> bool:
        return len(self._configure_driver_config_fields) > 0

    @rx.var
    def configure_driver_fields_with_values(self) -> list[dict[str, str | bool]]:
        """Structured field metadata plus current value for Reflex foreach rendering."""
        rows: list[dict[str, str | bool]] = []
        for field in self._configure_driver_config_fields:
            key = str(field.get("key", "")).strip()
            if not key:
                continue
            field_type = str(field.get("type", "text"))
            value = self._configure_driver_config_values.get(key, False if field_type == "checkbox" else "")
            row = dict(field)
            if field_type == "checkbox":
                row["value"] = bool(value)
            else:
                row["value"] = "" if value == "" else str(value)
            rows.append(row)
        return rows

    def _coerce_driver_field_value(self, field_type: str, value: str | bool):
        """Coerce form values into the proper JSON type for driver_config."""
        if field_type == "checkbox":
            return bool(value)

        if isinstance(value, bool):
            # Text/number inputs should not receive bool, but if they do, stringify.
            value = "true" if value else "false"

        raw = str(value).strip()
        if raw == "":
            return ""

        if field_type == "number":
            try:
                return int(raw)
            except ValueError:
                return raw

        if field_type == "float":
            try:
                return float(raw)
            except ValueError:
                return raw

        return raw

    def _normalize_driver_install_target(self, source: str) -> str:
        """Normalize package/source strings into pip-installable targets.

        Supports:
        - PyPI package names
        - Local paths
        - GitHub URLs without git+ prefix (auto-converted)
        - owner/repo shorthand (auto-converted to GitHub git URL)
        """
        target = source.strip()
        if not target:
            return target

        if target.startswith("git+"):
            return target

        # owner/repo shorthand -> git+https://github.com/owner/repo.git
        if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", target):
            return f"git+https://github.com/{target}.git"

        # github.com/owner/repo (no scheme) -> git+https://...
        if target.startswith("github.com/"):
            target = f"https://{target}"

        if target.startswith("http://") or target.startswith("https://"):
            is_archive = bool(re.search(r"(\.whl|\.zip|\.tar\.gz|\.tgz)$", target)) or "/archive/" in target
            if "github.com" in target and not is_archive:
                git_target = target.rstrip("/")
                if not git_target.endswith(".git"):
                    git_target = f"{git_target}.git"
                return f"git+{git_target}"

        return target

    def _rebuild_configure_device_json(self):
        """Rebuild the wizard's device JSON from top-level and form field values."""
        try:
            current = json.loads(self._configure_device_json)
        except json.JSONDecodeError:
            current = {}

        driver_config: dict[str, object] = {}
        for field in self._configure_driver_config_fields:
            key = str(field.get("key", "")).strip()
            if not key:
                continue
            field_type = str(field.get("type", "text"))
            value = self._configure_driver_config_values.get(key, "")
            coerced = self._coerce_driver_field_value(field_type, value)
            if coerced == "":
                continue
            driver_config[key] = coerced

        current["driver_config"] = driver_config
        current["driver_type"] = self._configure_driver_type
        current["registry_config"] = f"config://{self._configure_csv_name.strip()}"
        if "interval" not in current:
            current["interval"] = 5
        if "timezone" not in current:
            current["timezone"] = "US/Pacific"
        if "publish_breadth_first_all" not in current:
            current["publish_breadth_first_all"] = False
        if "publish_depth_first" not in current:
            current["publish_depth_first"] = False
        if "publish_breadth_first" not in current:
            current["publish_breadth_first"] = False

        self._configure_device_json = json.dumps(current, indent=2)

    @rx.var
    def show_live_edit_dialog(self) -> bool:
        return self._show_live_edit_dialog

    @rx.var
    def live_edit_content(self) -> str:
        return self._live_edit_content

    @rx.var
    def live_edit_saving(self) -> bool:
        return self._live_edit_saving

    @rx.event
    async def toggle_agent_tree(self, agent: str):
        """Expand/collapse the config key tree for any agent."""
        currently = self._expanded_agents.get(agent, False)
        self._expanded_agents[agent] = not currently
        if not currently:  # we just expanded
            yield DriverManagementState.fetch_agent_config_keys(agent)

    @rx.event(background=True)
    async def open_edit_live_config_key(self, agent: str, key: str):
        """Fetch config content via vctl config get and open the simple text editor."""
        async with self:
            self._live_key_loading = True
            self._live_editing_agent = agent
            self._live_editing_key = key
            current_uid = self.current_uid

        try:
            from ..thin_endpoint_wrappers import get_vctl_config_get
            response = await get_vctl_config_get(current_uid, agent, key)
            data = response.json() if hasattr(response, "json") else response
            content = data.get("content", "")
        except Exception as e:
            logger.error(f"Error fetching config key {key}: {e}")
            yield rx.toast.error(f"Failed to fetch config: {e}")
            async with self:
                self._live_key_loading = False
            return

        async with self:
            self._live_key_loading = False
            self._live_edit_content = content
            self._show_live_edit_dialog = True

    @rx.event
    def set_live_edit_content(self, value: str):
        """Update the live edit text area content."""
        self._live_edit_content = value

    @rx.event
    def close_live_edit_dialog(self):
        """Close the live config edit dialog."""
        self._show_live_edit_dialog = False
        self._live_edit_content = ""
        self._live_editing_key = ""
        self._live_editing_agent = ""

    @rx.event(background=True)
    async def save_live_edit_content(self):
        """Save the edited content back via vctl config store."""
        async with self:
            agent = self._live_editing_agent
            key = self._live_editing_key
            content = self._live_edit_content
            current_uid = self.current_uid
            self._live_edit_saving = True

        try:
            from ..thin_endpoint_wrappers import store_vctl_config_key
            await store_vctl_config_key(current_uid, agent, key, content)
            yield rx.toast.success(f"Saved {key}")
            async with self:
                self._show_live_edit_dialog = False
                self._live_edit_content = ""
                self._live_editing_key = ""
                self._live_editing_agent = ""
        except Exception as e:
            logger.error(f"Error storing config key {key}: {e}")
            yield rx.toast.error(f"Failed to save: {e}")
        finally:
            async with self:
                self._live_edit_saving = False

    @rx.event
    def open_delete_live_config_dialog(self, agent: str, key: str):
        """Open the confirm-delete dialog for a live config key."""
        self._live_editing_agent = agent
        self._live_editing_key = key
        self._show_delete_live_config_dialog = True

    @rx.event
    def close_delete_live_config_dialog(self):
        self._show_delete_live_config_dialog = False
        self._live_editing_key = ""
        self._live_editing_agent = ""

    @rx.event(background=True)
    async def confirm_delete_live_config_key(self):
        """Run vctl config delete <agent> <key> then refresh that agent's key list."""
        async with self:
            agent = self._live_editing_agent
            key = self._live_editing_key
            current_uid = self.current_uid
            self._show_delete_live_config_dialog = False
            self._live_key_loading = True

        try:
            from ..thin_endpoint_wrappers import delete_vctl_config_key
            await delete_vctl_config_key(current_uid, agent, key)
            yield rx.toast.success(f"Deleted {key}")
        except Exception as e:
            logger.error(f"Error deleting config key {key}: {e}")
            yield rx.toast.error(f"Failed to delete: {e}")
        finally:
            async with self:
                self._live_key_loading = False
                self._live_editing_key = ""
                self._live_editing_agent = ""
            yield DriverManagementState.fetch_agent_config_keys(agent)

    # Dialog actions — Configure Driver (from installed lib)
    @rx.event
    def open_configure_driver_dialog(self, pip_package_name: str):
        """Open the two-step configure wizard pre-filled with templates for a driver type."""
        from ..backend.models import DriverLibraryCatalog
        catalog = DriverLibraryCatalog()

        # Normalise: pip uses hyphens, catalog might too
        normalised = pip_package_name.strip().lower().replace("_", "-")
        entry = next(
            (d for d in catalog.drivers if d.pip_package.lower() == normalised),
            None,
        )

        if entry:
            driver_type = entry.driver_type
            self._configure_driver_name = entry.name
            csv_name = f"{driver_type}.csv"
            csv_content = entry.default_registry_csv
            try:
                driver_cfg_template = json.loads(entry.default_device_config or "{}")
                if not isinstance(driver_cfg_template, dict):
                    driver_cfg_template = {}
            except json.JSONDecodeError:
                driver_cfg_template = {}

            fields = entry.driver_config_fields or [
                {
                    "key": k,
                    "label": k.replace("_", " ").title(),
                    "type": "text",
                    "required": False,
                    "description": "",
                    "placeholder": str(v),
                }
                for k, v in driver_cfg_template.items()
            ]
            values: dict[str, str | bool] = {}
            for field in fields:
                key = str(field.get("key", "")).strip()
                if not key:
                    continue
                field_type = str(field.get("type", "text"))
                default_value = driver_cfg_template.get(key, "")
                if field_type == "checkbox":
                    values[key] = bool(default_value)
                elif default_value == "":
                    values[key] = ""
                else:
                    values[key] = str(default_value)

            default_device_config = {
                "driver_config": driver_cfg_template,
                "registry_config": f"config://{csv_name}",
                "interval": 5,
                "timezone": "US/Pacific",
                "heart_beat_point": "Heartbeat",
                "driver_type": driver_type,
                "publish_breadth_first_all": False,
                "publish_depth_first": False,
                "publish_breadth_first": False,
            }
            self._configure_required_agents = entry.required_agents
        else:
            driver_type = normalised.replace("volttron-lib-", "").replace("-driver", "")
            self._configure_driver_name = pip_package_name
            csv_name = f"{driver_type}.csv"
            csv_content = "Point Name,Volttron Point Name,Units,Writable,Type\n"
            fields = []
            values = {}
            default_device_config = {
                "driver_config": {},
                "registry_config": f"config://{csv_name}",
                "interval": 5,
                "timezone": "US/Pacific",
                "heart_beat_point": "Heartbeat",
                "driver_type": driver_type,
                "publish_breadth_first_all": False,
                "publish_depth_first": False,
                "publish_breadth_first": False,
            }
            self._configure_required_agents = []

        self._configure_driver_type = driver_type
        self._configure_driver_config_fields = fields
        self._configure_driver_config_values = values
        self._configure_device_name = f"devices/campus/building/{driver_type}"
        self._configure_device_json = json.dumps(default_device_config, indent=2)
        self._configure_csv_name = csv_name
        self._configure_csv_content = csv_content
        self._configure_step = 1
        self._form_errors = {}
        self._show_configure_driver_dialog = True

    @rx.event
    def set_configure_device_name(self, value: str):
        self._configure_device_name = value

    @rx.event
    def set_configure_device_json(self, value: str):
        self._configure_device_json = value

    @rx.event
    def set_configure_driver_field(self, key: str, value: str):
        if not key:
            return
        self._configure_driver_config_values[key] = value
        self._rebuild_configure_device_json()

    @rx.event
    def toggle_configure_driver_field(self, key: str, checked: bool):
        if not key:
            return
        self._configure_driver_config_values[key] = checked
        self._rebuild_configure_device_json()

    @rx.event
    def set_configure_csv_name(self, value: str):
        self._configure_csv_name = value
        self._rebuild_configure_device_json()

    @rx.event
    def set_configure_csv_content(self, value: str):
        self._configure_csv_content = value

    @rx.event
    def configure_next_step(self):
        """Advance from step 1 (device JSON) to step 2 (CSV)."""
        self._configure_step = 2

    @rx.event
    def configure_prev_step(self):
        """Go back from step 2 to step 1."""
        self._configure_step = 1

    @rx.event
    def close_configure_driver_dialog(self):
        self._show_configure_driver_dialog = False
        self._configure_step = 1
        self._configure_driver_type = ""
        self._configure_required_agents = []
        self._configure_driver_config_fields = []
        self._configure_driver_config_values = {}

    @rx.event(background=True)
    async def handle_configure_driver_save(self):
        """Save the driver config from the two-step configure wizard."""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                return

            device_path = self._configure_device_name.strip()
            device_json_text = self._configure_device_json.strip()
            csv_name = self._configure_csv_name.strip()
            csv_content = self._configure_csv_content
            current_uid = self.current_uid

            if not device_path or not csv_name:
                return

            platform = self.platforms[current_uid]

            # Ensure platform.driver agent exists in saved config
            if "platform.driver" not in platform.platform.agents:
                from ..backend.models import AgentCatalog
                catalog = AgentCatalog()
                if "platform.driver" in catalog.agents:
                    catalog_agent = catalog.agents["platform.driver"]
                    new_agent = AgentModelView(
                        identity="platform.driver",
                        source=catalog_agent.source,
                        config=json.dumps(catalog_agent.default_config, indent=2),
                        config_store=[],
                        is_new=True,
                        config_store_allowed=catalog_agent.config_store_allowed,
                        routing_id=generate_unique_uid(),
                    )
                    platform.platform.agents["platform.driver"] = new_agent

            agent = platform.platform.agents["platform.driver"]

            # Clean up any stale entries for this device path or CSV name.
            # If there's an existing device entry pointing to a different CSV, remove that CSV too.
            paths_to_remove: set[str] = {device_path, csv_name}
            for e in list(agent.config_store):
                if e.path == device_path:
                    try:
                        old_cfg = json.loads(e.value)
                        old_csv = old_cfg.get("registry_config", "").replace("config://", "")
                        if old_csv:
                            paths_to_remove.add(old_csv)
                    except Exception:
                        pass
            # Remove stale entries in-place (can't reassign on proxy in background task)
            for e in list(agent.config_store):
                if e.path in paths_to_remove:
                    agent.config_store.remove(e)

            # Add registry CSV entry
            if not csv_name.endswith(".csv"):
                csv_name += ".csv"
            registry_entry = ConfigStoreEntryModelView(
                path=csv_name,
                data_type="CSV",
                value=csv_content,
                component_id=generate_unique_uid(),
                uncommitted=True,
                valid=True,
            )
            registry_entry.safe_entry = {
                "path": csv_name,
                "data_type": "CSV",
                "value": csv_content,
                "component_id": registry_entry.component_id,
                "csv_variants": ""
            }
            agent.config_store.append(registry_entry)

            # Add device JSON entry — use the raw text as-is
            device_entry = ConfigStoreEntryModelView(
                path=device_path,
                data_type="JSON",
                value=device_json_text,
                component_id=generate_unique_uid(),
                uncommitted=True,
                valid=True,
            )
            device_entry.safe_entry = {
                "path": device_path,
                "data_type": "JSON",
                "value": device_json_text,
                "component_id": device_entry.component_id,
                "csv_variants": ""
            }
            agent.config_store.append(device_entry)

        # Save platform config to API
        try:
            async with self:
                platform_snapshot = self.platforms[current_uid]
            await _save_platform_config(platform_snapshot, current_uid)
            yield rx.toast.success(f"Driver config saved to {device_path}")
        except Exception as e:
            logger.error(f"Failed to save platform: {e}")
            yield rx.toast.error(f"Failed to save: {e}")
            async with self:
                self._show_configure_driver_dialog = False
            return

        # Auto-deploy to the running VOLTTRON instance
        async with self:
            self._deploying_configs = True
        try:
            from ..thin_endpoint_wrappers import deploy_agent_config_store
            response = await deploy_agent_config_store(current_uid, "platform.driver")
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Config deployment result: {result}")
                async with self:
                    platform = self.platforms[current_uid]
                    platform.deployed = True
                    platform.platform.in_file = True
                    platform.new_instance = False
                    platform.platform.safe_platform = platform.platform.to_dict()
                yield rx.toast.success("Driver configs deployed to running platform")
            else:
                logger.error(f"Failed to deploy configs: {response.text}")
                yield rx.toast.error("Saved but failed to deploy — use 'Deploy Configs' manually")
        except Exception as e:
            logger.error(f"Error deploying configs: {e}")
            yield rx.toast.error(f"Saved but deploy failed: {e}")
        finally:
            async with self:
                self._deploying_configs = False

        async with self:
            self._show_configure_driver_dialog = False

        # Refresh the config store tree so the new entries appear
        yield DriverManagementState.fetch_vctl_config_list

    # Dialog actions — Driver Library Install
    @rx.event
    def open_install_driver_lib_dialog(self):
        """Open dialog to install a driver library."""
        self._show_install_driver_lib_dialog = True
        self._install_driver_lib_mode = "catalog"
        self._selected_driver_lib = ""
        self._selected_local_driver_lib = ""
        self._custom_driver_lib = ""
        self._driver_lib_install_result = ""
        return DriverManagementState.load_local_driver_libraries

    @rx.event
    def close_install_driver_lib_dialog(self):
        self._show_install_driver_lib_dialog = False

    @rx.event
    def set_install_driver_lib_mode(self, value: str):
        self._install_driver_lib_mode = value

    @rx.event
    def set_selected_driver_lib(self, value: str):
        self._selected_driver_lib = value
        self._install_driver_lib_mode = "catalog"
        self._selected_local_driver_lib = ""
        # Clear custom when selecting from catalog
        if value:
            self._custom_driver_lib = ""

    @rx.event
    def set_custom_driver_lib(self, value: str):
        self._custom_driver_lib = value
        self._install_driver_lib_mode = "manual"
        self._selected_driver_lib = ""
        self._selected_local_driver_lib = ""
        # Clear catalog selection when typing custom
        if value.strip():
            self._selected_driver_lib = ""

    @rx.event
    def select_local_driver_lib(self, path: str):
        self._install_driver_lib_mode = "local"
        self._selected_local_driver_lib = path
        self._selected_driver_lib = ""
        self._custom_driver_lib = ""

    @rx.event(background=True)
    async def load_local_driver_libraries(self):
        """Load local driver libraries from the local workspace scan results."""
        async with self:
            self._loading_local_driver_libs = True

        libs: list[dict[str, str]] = []
        try:
            from ..thin_endpoint_wrappers import get_local_agents

            agents = await get_local_agents()
            for agent in agents:
                raw_identity = str(getattr(agent, "identity", "") or "")
                source_path = str(getattr(agent, "local_path", "") or getattr(agent, "source", "") or "")
                if not source_path:
                    continue

                normalized_identity = raw_identity.lower()
                source_lower = source_path.lower()
                if "driver" not in normalized_identity and "driver" not in source_lower:
                    continue

                description = ""
                default_config = getattr(agent, "default_config", {})
                if isinstance(default_config, dict):
                    description = str(default_config.get("_description", "") or "")

                libs.append(
                    {
                        "name": raw_identity,
                        "path": source_path,
                        "description": description,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to load local driver libraries: {e}")
            libs = []

        async with self:
            self._local_driver_libs = libs
            self._loading_local_driver_libs = False

    @rx.event
    async def handle_install_driver_lib(self):
        """Install the selected driver library via pip into the VOLTTRON venv."""
        package = self.driver_lib_to_install
        if not package:
            return

        install_target = self._normalize_driver_install_target(package)
        if package == "volttron-lib-homeassistant-driver":
            install_target = "git+https://github.com/eclipse-volttron/volttron-lib-homeassistant-driver.git"

        self._installing_driver_lib = True
        self._driver_lib_install_result = ""
        yield

        try:
            from ..thin_endpoint_wrappers import install_driver_library
            platform_id = self.current_uid
            if not platform_id:
                self._driver_lib_install_result = "No platform selected"
                self._installing_driver_lib = False
                yield
                return

            response = await install_driver_library(platform_id, install_target)
            if response.status_code == 200:
                result = response.json()
                self._driver_lib_install_result = f"✅ {result.get('message', 'Installed successfully')}"
                yield rx.toast.success(f"Installed {package}")
                # Refresh the installed drivers list
                yield DriverManagementState.fetch_installed_driver_libs
            else:
                detail = response.json().get("detail", response.text) if response.text else "Unknown error"
                self._driver_lib_install_result = f"❌ {detail}"
                yield rx.toast.error(f"Failed to install {package}")
        except Exception as e:
            logger.error(f"Error installing driver library {package}: {e}")
            self._driver_lib_install_result = f"❌ {str(e)}"
            yield rx.toast.error(f"Error: {e}")
        finally:
            self._installing_driver_lib = False
            yield

    # Dialog actions — Driver Config
    @rx.event
    def open_add_driver_dialog(self):
        """Open dialog to add new driver"""
        self._show_add_driver_dialog = True
        self._driver_type = "fake"
        self._campus = "campus"
        self._building = "building"
        self._unit = "fake"
        self._interval = 5
        self._timezone = "US/Pacific"
        self._heart_beat_point = "Heartbeat"
        self._registry_config_name = ""
        self._new_registry_name = ""
        self._new_registry_content = ""
        self._driver_config_json = "{}"
        self._form_errors = {}

    @rx.event
    def close_add_driver_dialog(self):
        """Close add driver dialog"""
        self._show_add_driver_dialog = False

    @rx.event
    def open_edit_driver_dialog(self, driver_path: str):
        """Open dialog to edit existing driver"""
        # Find the driver config
        driver = next((d for d in self.driver_configs if d["path"] == driver_path), None)
        if not driver:
            return
        
        self._editing_driver_path = driver_path
        self._editing_driver_config_id = driver["config_id"]
        self._driver_type = driver["driver_type"]
        self._campus = driver["campus"]
        self._building = driver["building"]
        self._unit = driver["unit"]
        self._interval = driver["interval"]
        self._timezone = driver["timezone"]
        self._heart_beat_point = driver.get("heart_beat_point", "")
        self._registry_config_name = driver["registry"]
        self._driver_config_json = json.dumps(driver.get("driver_config", {}), indent=2)
        self._show_edit_driver_dialog = True

    @rx.event
    def close_edit_driver_dialog(self):
        """Close edit driver dialog"""
        self._show_edit_driver_dialog = False

    @rx.event
    def open_delete_driver_dialog(self, driver_path: str, config_id: str):
        """Open dialog to confirm driver deletion"""
        self._editing_driver_path = driver_path
        self._editing_driver_config_id = config_id
        self._show_delete_driver_dialog = True

    @rx.event
    def close_delete_driver_dialog(self):
        """Close delete driver dialog"""
        self._show_delete_driver_dialog = False

    # Form field setters
    @rx.event
    def set_driver_type(self, value: str):
        self._driver_type = value

    @rx.event
    def set_campus(self, value: str):
        self._campus = value.strip()

    @rx.event
    def set_building(self, value: str):
        self._building = value.strip()

    @rx.event
    def set_unit(self, value: str):
        self._unit = value.strip()

    @rx.event
    def set_interval(self, value: str):
        try:
            self._interval = int(value)
        except ValueError:
            pass

    @rx.event
    def set_timezone(self, value: str):
        self._timezone = value

    @rx.event
    def set_heart_beat_point(self, value: str):
        self._heart_beat_point = value

    @rx.event
    def set_registry_config_name(self, value: str):
        self._registry_config_name = value
        # Clear new registry fields if selecting existing
        if value:
            self._new_registry_name = ""
            self._new_registry_content = ""

    @rx.event
    def set_new_registry_name(self, value: str):
        self._new_registry_name = value.strip()

    @rx.event
    def set_new_registry_content(self, value: str):
        self._new_registry_content = value

    @rx.event
    def set_driver_config_json(self, value: str):
        self._driver_config_json = value

    # CRUD operations
    @rx.event(background=True)
    async def handle_add_driver(self):
        """Add new driver configuration to platform.driver"""
        async with self:
            if not self.can_add_driver:
                return
            
            # Get or create platform.driver agent
            if not self.current_uid or self.current_uid not in self.platforms:
                return
            
            platform = self.platforms[self.current_uid]
            
            # Ensure platform.driver exists in saved config (it may be running live without being saved)
            if "platform.driver" not in platform.platform.agents:
                from ..backend.models import AgentCatalog
                catalog = AgentCatalog()
                if "platform.driver" in catalog.agents:
                    catalog_agent = catalog.agents["platform.driver"]
                    new_agent = AgentModelView(
                        identity="platform.driver",
                        source=catalog_agent.source,
                        config=json.dumps(catalog_agent.default_config, indent=2),
                        config_store=[],
                        is_new=True,
                        config_store_allowed=catalog_agent.config_store_allowed,
                        routing_id=generate_unique_uid(),
                    )
                    platform.platform.agents["platform.driver"] = new_agent
            
            agent = platform.platform.agents["platform.driver"]
            
            # Add registry if new one provided
            registry_name = self._registry_config_name
            if self._new_registry_name and self._new_registry_content:
                registry_name = self._new_registry_name
                if not registry_name.endswith(".csv"):
                    registry_name += ".csv"
                
                # Create registry config entry
                registry_entry = ConfigStoreEntryModelView(
                    path=registry_name,
                    data_type="CSV",
                    value=self._new_registry_content,
                    component_id=generate_unique_uid(),
                    uncommitted=True,
                    valid=True,
                )
                registry_entry.safe_entry = {
                    "path": registry_name,
                    "data_type": "CSV",
                    "value": self._new_registry_content,
                    "component_id": registry_entry.component_id,
                    "csv_variants": ""
                }
                agent.config_store.append(registry_entry)
            
            # Generate device config JSON
            device_config = {
                "driver_config": {},
                "driver_type": self._driver_type,
                "registry_config": f"config://{registry_name}",
                "interval": self._interval,
                "timezone": self._timezone,
                "publish_breadth_first_all": False,
                "publish_depth_first": False,
                "publish_breadth_first": False,
            }
            
            # Parse advanced driver_config if provided
            if self._driver_config_json.strip() and self._driver_config_json.strip() != "{}":
                try:
                    device_config["driver_config"] = json.loads(self._driver_config_json)
                except json.JSONDecodeError:
                    pass
            
            if self._heart_beat_point:
                device_config["heart_beat_point"] = self._heart_beat_point
            
            # Create device config entry
            device_path = self.driver_path
            device_entry = ConfigStoreEntryModelView(
                path=device_path,
                data_type="JSON",
                value=json.dumps(device_config, indent=2),
                component_id=generate_unique_uid(),
                uncommitted=True,
                valid=True,
            )
            device_entry.safe_entry = {
                "path": device_path,
                "data_type": "JSON",
                "value": json.dumps(device_config, indent=2),
                "component_id": device_entry.component_id,
                "csv_variants": ""
            }
            agent.config_store.append(device_entry)
            
            # Capture values for API call
            current_uid = self.current_uid
        
        # Save platform (network call outside async with self)
        try:
            async with self:
                platform_snapshot = self.platforms[current_uid]
            await _save_platform_config(platform_snapshot, current_uid)
        except Exception as e:
            logger.error(f"Failed to save platform: {e}")
        
        # Close dialog
        async with self:
            self._show_add_driver_dialog = False

    @rx.event(background=True)
    async def handle_edit_driver(self):
        """Update existing driver configuration"""
        async with self:
            if not self.can_add_driver or not self._editing_driver_config_id:
                return
            
            if not self.current_uid or self.current_uid not in self.platforms:
                return
            
            platform = self.platforms[self.current_uid]
            agent = platform.platform.agents.get("platform.driver")
            if not agent:
                return
            
            # Find and update the device config entry
            for config in agent.config_store:
                if config.component_id == self._editing_driver_config_id:
                    # Generate updated device config
                    device_config = {
                        "driver_config": {},
                        "driver_type": self._driver_type,
                        "registry_config": f"config://{self._registry_config_name}",
                        "interval": self._interval,
                        "timezone": self._timezone,
                        "campus": self._campus,
                        "building": self._building,
                        "unit": self._unit,
                    }
                    
                    if self._driver_config_json.strip() and self._driver_config_json.strip() != "{}":
                        try:
                            device_config["driver_config"] = json.loads(self._driver_config_json)
                        except json.JSONDecodeError:
                            pass
                    
                    if self._heart_beat_point:
                        device_config["heart_beat_point"] = self._heart_beat_point
                    
                    # Update path if location changed
                    new_path = self.driver_path
                    config.path = new_path
                    config.value = json.dumps(device_config, indent=2)
                    config.uncommitted = True
                    
                    break
            
            # Capture values for API call
            current_uid = self.current_uid
        
        # Save platform (network call outside async with self)
        try:
            async with self:
                platform_snapshot = self.platforms[current_uid]
            await _save_platform_config(platform_snapshot, current_uid)
        except Exception as e:
            logger.error(f"Failed to save platform: {e}")
        
        async with self:
            self._show_edit_driver_dialog = False

    @rx.event(background=True)
    async def handle_delete_driver(self):
        """Delete driver configuration"""
        async with self:
            if not self._editing_driver_config_id:
                return
            
            if not self.current_uid or self.current_uid not in self.platforms:
                return
            
            platform = self.platforms[self.current_uid]
            agent = platform.platform.agents.get("platform.driver")
            if not agent:
                return
            
            # Remove the device config entry
            agent.config_store = [
                config for config in agent.config_store 
                if config.component_id != self._editing_driver_config_id
            ]
            
            # Capture values for API call
            current_uid = self.current_uid
        
        # Save platform (network call outside async with self)
        try:
            async with self:
                platform_snapshot = self.platforms[current_uid]
            await _save_platform_config(platform_snapshot, current_uid)
        except Exception as e:
            logger.error(f"Failed to save platform: {e}")
        
        async with self:
            self._show_delete_driver_dialog = False

    @rx.event(background=True)
    async def deploy_driver_configs(self):
        """Deploy platform.driver config store to running VOLTTRON instance"""
        async with self:
            if not self.current_uid or self.current_uid not in self.platforms:
                return
            
            platform = self.platforms[self.current_uid]
            if "platform.driver" not in platform.platform.agents:
                logger.warning("No platform.driver agent found to deploy configs")
                return
            
            current_uid = self.current_uid
            self._deploying_configs = True
        
        try:
            from ..thin_endpoint_wrappers import deploy_agent_config_store
            response = await deploy_agent_config_store(current_uid, "platform.driver")
            
            # Parse response
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Config deployment result: {result}")
                # Could add a toast notification here
            else:
                logger.error(f"Failed to deploy configs: {response.text}")
                
        except Exception as e:
            logger.error(f"Error deploying configs: {e}")
        finally:
            async with self:
                self._deploying_configs = False
