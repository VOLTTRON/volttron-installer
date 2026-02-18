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


class DriverManagementState(PlatformDeploymentState):
    """State for managing platform driver configurations"""
    
    # Dialog visibility
    _show_add_driver_dialog: bool = False
    _show_edit_driver_dialog: bool = False
    _show_delete_driver_dialog: bool = False
    _show_deploy_drivers_dialog: bool = False
    
    # Driver form fields
    _driver_type: str = "fakedriver"
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
        # Also accept it when the live VOLTTRON instance reports it as running
        return "platform.driver" in self.platform_agents

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

    # Dialog actions
    @rx.event
    def open_add_driver_dialog(self):
        """Open dialog to add new driver"""
        self._show_add_driver_dialog = True
        self._driver_type = "fakedriver"
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
            "campus": self._campus,
            "building": self._building,
            "unit": self._unit,
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
        from ..thin_endpoint_wrappers import put_platform
        try:
            await put_platform(self.current_uid, platform.platform.to_dict())
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
        from ..thin_endpoint_wrappers import put_platform
        try:
            await put_platform(self.current_uid, platform.platform.to_dict())
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
        from ..thin_endpoint_wrappers import put_platform
        try:
            await put_platform(self.current_uid, platform.platform.to_dict())
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
