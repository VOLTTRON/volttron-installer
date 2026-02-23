"""
Driver Management State - Handles CRUD operations for platform drivers.

Platform drivers are configurations loaded by the platform.driver agent.
Each driver consists of:
- Registry CSV: Defines device data points
- Device Config JSON: Specifies driver type, location, registry reference
"""

import reflex as rx
import json
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
    _installing_driver_lib: bool = False
    _driver_lib_install_result: str = ""
    
    # Installed driver libraries (from pip list)
    _installed_driver_libs: list[dict[str, str]] = []  # [{"name": ..., "version": ...}]
    _loading_installed_drivers: bool = False

    # vctl config list state
    _vctl_config_agents: list[str] = []        # agents with config store entries
    _vctl_config_keys: list[str] = []          # config keys for platform.driver
    _vctl_config_loading: bool = False
    _platform_driver_tree_expanded: bool = False

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
    def driver_lib_to_install(self) -> str:
        """The pip package that will be installed — either catalog selection or custom."""
        if self._custom_driver_lib.strip():
            return self._custom_driver_lib.strip()
        return self._selected_driver_lib

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
    def vctl_config_keys(self) -> list[str]:
        return self._vctl_config_keys

    @rx.var
    def vctl_config_loading(self) -> bool:
        return self._vctl_config_loading

    @rx.var
    def platform_driver_tree_expanded(self) -> bool:
        return self._platform_driver_tree_expanded

    @rx.var
    def platform_driver_in_config_store(self) -> bool:
        """True if platform.driver appears in vctl config list output."""
        return "platform.driver" in self._vctl_config_agents

    @rx.event
    async def fetch_vctl_config_list(self):
        """Run vctl config list to get agents with config store entries."""
        if not self.current_uid:
            return
        self._vctl_config_loading = True
        yield
        try:
            from ..thin_endpoint_wrappers import get_vctl_config_list, ApiError
            response = await get_vctl_config_list(self.current_uid)
            self._vctl_config_agents = response.get("entries", [])
            # If platform.driver is present and tree was expanded, refresh its keys too
            if self._platform_driver_tree_expanded and "platform.driver" in self._vctl_config_agents:
                yield DriverManagementState.fetch_platform_driver_config_keys
        except Exception as e:
            logger.error(f"Error running vctl config list: {e}")
            self._vctl_config_agents = []
        finally:
            self._vctl_config_loading = False
            yield

    @rx.event
    async def fetch_platform_driver_config_keys(self):
        """Run vctl config list platform.driver to get its config keys."""
        if not self.current_uid:
            return
        self._vctl_config_loading = True
        yield
        try:
            from ..thin_endpoint_wrappers import get_vctl_config_list, ApiError
            response = await get_vctl_config_list(self.current_uid, "platform.driver")
            self._vctl_config_keys = response.get("entries", [])
        except Exception as e:
            logger.error(f"Error running vctl config list platform.driver: {e}")
            self._vctl_config_keys = []
        finally:
            self._vctl_config_loading = False
            yield

    @rx.event
    async def toggle_platform_driver_tree(self):
        """Expand/collapse the platform.driver config tree."""
        self._platform_driver_tree_expanded = not self._platform_driver_tree_expanded
        if self._platform_driver_tree_expanded and "platform.driver" in self._vctl_config_agents:
            yield DriverManagementState.fetch_platform_driver_config_keys

    # Dialog actions — Configure Driver (from installed lib)
    @rx.event
    def open_configure_driver_dialog(self, pip_package_name: str):
        """Open the configure dialog pre-filled with templates for a driver type.

        Looks up the installed pip_package_name in the catalog to find the
        driver_type and default templates, then populates the form fields.
        """
        from ..backend.models import DriverLibraryCatalog
        catalog = DriverLibraryCatalog()

        # Normalise: pip uses hyphens, catalog might too
        normalised = pip_package_name.strip().lower().replace("_", "-")
        entry = next(
            (d for d in catalog.drivers if d.pip_package.lower() == normalised),
            None,
        )

        if entry:
            self._driver_type = entry.driver_type
            self._configure_driver_name = entry.name
            self._new_registry_name = f"{entry.driver_type}_registry.csv"
            self._new_registry_content = entry.default_registry_csv
            self._driver_config_json = entry.default_device_config or "{}"
        else:
            # Unknown driver — open with blanks
            self._driver_type = normalised.replace("volttron-lib-", "").replace("-driver", "")
            self._configure_driver_name = pip_package_name
            self._new_registry_name = "registry.csv"
            self._new_registry_content = "Point Name,Volttron Point Name,Units,Writable,Type\n"
            self._driver_config_json = "{}"

        # Sensible defaults for location fields
        self._campus = "campus"
        self._building = "building"
        self._unit = self._driver_type
        self._interval = 5
        self._timezone = "US/Pacific"
        self._heart_beat_point = "Heartbeat"
        self._registry_config_name = ""  # force "new registry" path
        self._form_errors = {}
        self._show_configure_driver_dialog = True

    @rx.event
    def close_configure_driver_dialog(self):
        self._show_configure_driver_dialog = False

    @rx.event
    async def handle_configure_driver_save(self):
        """Save the driver config from the configure dialog.

        Reuses the same logic as handle_add_driver.
        """
        if not self.can_add_driver:
            return

        if not self.current_uid or self.current_uid not in self.platforms:
            return

        platform = self.platforms[self.current_uid]

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

        # Add registry
        registry_name = self._registry_config_name
        if self._new_registry_name and self._new_registry_content:
            registry_name = self._new_registry_name
            if not registry_name.endswith(".csv"):
                registry_name += ".csv"
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

        # Build device config
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
        if self._driver_config_json.strip() and self._driver_config_json.strip() != "{}":
            try:
                device_config["driver_config"] = json.loads(self._driver_config_json)
            except json.JSONDecodeError:
                pass
        if self._heart_beat_point:
            device_config["heart_beat_point"] = self._heart_beat_point

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

        # Save platform config to API
        try:
            await _save_platform_config(platform, self.current_uid)
            yield rx.toast.success(f"Driver config saved to {device_path}")
        except Exception as e:
            logger.error(f"Failed to save platform: {e}")
            yield rx.toast.error(f"Failed to save: {e}")
            self._show_configure_driver_dialog = False
            yield
            return

        # Auto-deploy to the running VOLTTRON instance
        self._deploying_configs = True
        yield
        try:
            from ..thin_endpoint_wrappers import deploy_agent_config_store
            response = await deploy_agent_config_store(self.current_uid, "platform.driver")
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Config deployment result: {result}")
                # Mark platform as deployed since we successfully pushed configs
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
            self._deploying_configs = False

        self._show_configure_driver_dialog = False
        yield

    # Dialog actions — Driver Library Install
    @rx.event
    def open_install_driver_lib_dialog(self):
        """Open dialog to install a driver library."""
        self._show_install_driver_lib_dialog = True
        self._selected_driver_lib = ""
        self._custom_driver_lib = ""
        self._driver_lib_install_result = ""

    @rx.event
    def close_install_driver_lib_dialog(self):
        self._show_install_driver_lib_dialog = False

    @rx.event
    def set_selected_driver_lib(self, value: str):
        self._selected_driver_lib = value
        # Clear custom when selecting from catalog
        if value:
            self._custom_driver_lib = ""

    @rx.event
    def set_custom_driver_lib(self, value: str):
        self._custom_driver_lib = value
        # Clear catalog selection when typing custom
        if value.strip():
            self._selected_driver_lib = ""

    @rx.event
    async def handle_install_driver_lib(self):
        """Install the selected driver library via pip into the VOLTTRON venv."""
        package = self.driver_lib_to_install
        if not package:
            return

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

            response = await install_driver_library(platform_id, package)
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
    @rx.event
    async def handle_add_driver(self):
        """Add new driver configuration to platform.driver"""
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
        
        # Save platform
        try:
            await _save_platform_config(platform, self.current_uid)
        except Exception as e:
            logger.error(f"Failed to save platform: {e}")
        
        # Close dialog
        self._show_add_driver_dialog = False
        
        # Refresh platform status
        yield

    @rx.event
    async def handle_edit_driver(self):
        """Update existing driver configuration"""
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
        
        # Save platform
        try:
            await _save_platform_config(platform, self.current_uid)
        except Exception as e:
            logger.error(f"Failed to save platform: {e}")
        
        self._show_edit_driver_dialog = False
        yield

    @rx.event
    async def handle_delete_driver(self):
        """Delete driver configuration"""
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
        
        # Save platform
        try:
            await _save_platform_config(platform, self.current_uid)
        except Exception as e:
            logger.error(f"Failed to save platform: {e}")
        
        self._show_delete_driver_dialog = False
        yield

    @rx.event
    async def deploy_driver_configs(self):
        """Deploy platform.driver config store to running VOLTTRON instance"""
        if not self.current_uid or self.current_uid not in self.platforms:
            return
        
        platform = self.platforms[self.current_uid]
        if "platform.driver" not in platform.platform.agents:
            logger.warning("No platform.driver agent found to deploy configs")
            return
        
        self._deploying_configs = True
        yield
        
        try:
            from ..thin_endpoint_wrappers import deploy_agent_config_store
            response = await deploy_agent_config_store(self.current_uid, "platform.driver")
            
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
            self._deploying_configs = False
            yield
