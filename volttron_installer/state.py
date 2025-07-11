import reflex as rx
from .settings import get_settings
from .model_views import *
from .utils.create_component_uid import generate_unique_uid
from .models import *
from .utils.conversion_methods import json_string_to_csv_string, csv_string_to_json_string, identify_string_format, csv_string_to_usable_dict
from .utils.validate_content import check_json, check_csv, check_path, check_yaml, check_regular_expression
from .utils.create_csv_string import create_csv_string, create_and_validate_csv_string
from .navigation.state import NavigationState
from .backend.models import AgentType, HostEntry, PlatformConfig, PlatformDefinition, ConfigStoreEntry, AgentDefinition, CreatePlatformRequest, CreateOrUpdateHostEntryRequest, ToolRequest, BACnetDevice
from .utils.create_component_uid import generate_unique_uid
from .utils.conversion_methods import csv_string_to_usable_dict
from .utils.validate_content import check_json
from .utils.prettify import prettify_json
from .utils import delete_file
from loguru import logger
from typing import Dict, Optional, List
from .thin_endpoint_wrappers import *
import string, random, json, csv, yaml, re, io, asyncio
from copy import deepcopy
from typing import Literal

class AppState(rx.State):
    """The app state."""
    _sidebar_page_selected: str = "overview"
    tool_accordion_value: str ="tools"

    # Events
    @rx.var
    def sidebar_selected_page(self) -> str:
        self._sidebar_page_selected = self.router.page.raw_path if self.router.page.raw_path != "/" else "overview"
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
    def select_overview(self):
        self.sidebar_page_selected = "overview"
        # yield NavigationState.route_to_index()


class ToolState(rx.State):
    """State for managing tool lifecycle."""
    
    # Track running tools
    _running_tools: dict[str, bool] = {}
    loading_tools: dict[str, bool] = {}
    error_message: Optional[str] = None
    
    # Tool configuration
    tool_configs: dict[str, ToolRequest] = {
        "bacnet_scan_tool": ToolRequest(
            tool_name="bacnet_scan_tool",
            module_path="bacnet_scan_tool.main:app",
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

    @rx.event
    async def start_tool(self, tool_id: str):
        """Start a specific tool service."""
        logger.debug(f"starting tool : {tool_id}")
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
            config = self.tool_configs[tool_id]
            logger.debug("calling api...")
            # Call API to start the tool
            await start_tool(config)
            self.running_tools[tool_id] = True
            logger.debug("tool started")
            
        except Exception as e:
            logger.debug(f"Error starting tool: {str(e)}")
        finally:
            # Clear loading state
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

async def __agents_off_catalog__() -> list[AgentModelView]:
    catalog: dict[str, AgentType] = await get_agent_catalog()
    agent_list: list[AgentModelView] = []

    for identity, agent in catalog.items():
        agent_list.append(
            AgentModelView(
                identity=str(identity),
                source=agent.source,
                safe_agent={
                    "identity" : identity,
                    "source" : agent.source,
                    "config" : json.dumps(agent.default_config, indent=4),
                    "config_store" : {
                        path : {
                            "path" : path,
                            "data_type" : config.data_type,
                            "value" : config.value
                        }
                        for path, config in agent.default_config_store.items()
                    }
                },
                config_store_allowed = agent.config_store_allowed,
                config_store=[
                    ConfigStoreEntryModelView(
                        path=path,
                        data_type=entry.data_type,
                        value=str(entry.value),
                        uncommitted=False,
                        is_new=True,
                        safe_entry={
                            "path": path,
                            "data_type": entry.data_type,
                            "value": str(entry.value)
                        }
                    ) for path, entry in agent.default_config_store.items()
                ],
                config=json.dumps(agent.default_config, indent=4),
            )
        )
    return agent_list

async def __instances_from_api__() -> dict[str, Instance]:
    platforms: list[PlatformDefinition] = await get_all_platforms()
    hosts: list[HostEntry] = await get_hosts()
    host_by_id: dict[str, HostEntry] = {}
    for h in hosts:
        # Before we add to the map, lets clear None types for empty strings...
        # alternatively, we could use model_dump() and replace kv pairs with None types
        # to empty strings
        h = HostEntry(**h.to_dict())
        host_by_id[h.id] = h
    
    instances: dict[str, Instance] = {}

    # Creating platform model views, and instances
    for p in platforms:
        working_host_entry = host_by_id[p.host_id]
        host = HostEntryModelView(
            id=p.host_id,
            ansible_user=working_host_entry.ansible_user,
            ansible_host=working_host_entry.ansible_host,
            # For later type validation
            ansible_port=str(working_host_entry.ansible_port),
            http_proxy=working_host_entry.http_proxy,
            https_proxy=working_host_entry.https_proxy,
            volttron_venv=working_host_entry.volttron_venv,
            volttron_home=working_host_entry.volttron_home,
        )

        instance = {
            p.config.instance_name: Instance(
                host=host,
                platform=PlatformModelView(
                    in_file=True,
                    config=PlatformConfigModelView(
                        instance_name=p.config.instance_name,
                        vip_address=p.config.vip_address,
                    ),
                    agents={
                        identity: AgentModelView(
                            identity=identity,
                            source=agent.source,
                            routing_id=identity,
                            safe_agent={
                                "identity" : identity,
                                "source" : agent.source,
                                "config": agent.config,
                            },
                            config_store_allowed=agent.config_store_allowed,
                            config_store=[
                                ConfigStoreEntryModelView(
                                    path=path,
                                    data_type=entry.data_type,
                                    value=str(entry.value),
                                    uncommitted=False,
                                    component_id=generate_unique_uid(),
                                    safe_entry={
                                        "path": path,
                                        "data_type": entry.data_type,
                                        "value": str(entry.value)
                                    },
                                ) for path, entry in agent.config_store.items()
                            ],
                            config="" if agent.config is None else prettify_json(agent.config)[0],
                        )
                        for identity, agent in p.agents.items()
                    }
                ),
                new_instance = False,
                safe_host_entry=host.to_dict(),
            )
        }
        
        instances.update(instance)
    for uid, instance in instances.items():
        instance.platform.safe_platform = instance.platform.to_dict()
        for agent in instance.platform.agents.values():
            for config in agent.config_store:
                # Assign the config's safe_entry
                config.safe_entry = config.dict()
                if config.data_type == "CSV":
                    usable_csv = csv_string_to_usable_dict(config.value)
                    config.csv_variants["Custom"] = usable_csv
            # After going through the agent's config store and assigning the safe entries,
            # we can now assign the agent's safe_agent
            agent.safe_agent = agent.to_dict()

    return instances

class PlatformPageState(rx.State):
    #TODO once we save a platform, we create a routing id 
    # off of it's instance name, and redirect the user to 
    # platforms/x, maybe we might have to delete the old 
    # routing id
    platforms: dict[str, Instance] = {
        # "new": Instance(
        #     host=HostEntryModelView(),
        #     platform=PlatformModelView()
        # )
    }
    list_of_agents: list[AgentModelView] = []

    _host_resolvable: bool = True
    _host_pinging: bool = False
    
    # this var tracks if the host_id that the user is inputting is resolved.
    # as the user inputs a host, we make sure this is false inside of self.update_detail,
    # so we cant save the instance until the host text box has been blurred. once it has, 
    # we can check if the host is reachable or not. if it is, we set this to true.
    _host_resolved: bool = False


    # Vars
    @rx.var(cache=True)
    def current_uid(self) -> str:
        return self.router.page.params.get("uid", "")

    @rx.var(cache=True)
    def in_file_platforms(self) -> list[Instance]:
        return [instance for instance in self.platforms.values() if instance.platform.in_file]
    
    @rx.var
    def new_agents_list(self) -> list[str]:
        if self.current_uid == "":
            return []
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return []
        # logger.debug(f"nah because new agents are : {[agent.identity for agent in working_platform.platform.agents.values() if not agent.is_new]}")
        return [agent.identity for agent in working_platform.platform.agents.values() if not agent.is_new]

    @rx.var
    def platform_title(self) -> str:
        if self.current_uid == "":
            return " "
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return " "
        else:
            return working_platform.platform.safe_platform['config']['instance_name']

    # === vars for platform details ===
    @rx.var
    def password_field(self) -> str:
        if self.current_uid == "":
            return ""
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return ""
        return working_platform.password

    @rx.var
    def platform_deployed(self) -> bool:
        if self.current_uid == "":
            return False
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return ""
        return working_platform.deployed

    # === end of platform detail vars ===

    # ==== vars for connection validation ===
    @rx.var
    def host_resolved(self) -> bool: return self._host_resolved

    @rx.var
    def connection_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[0]
    
    @rx.var
    def host_pinging(self) -> bool:
        return self._host_pinging

    @rx.var
    def is_host_resolvable(self) -> bool:
        return self._host_resolvable


    @rx.var
    def connection_id_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[1]["id"]
    
    @rx.var
    def connection_ansible_user_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[1]["ansible_user"]
    
    @rx.var
    def connection_ansible_host_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[1]["ansible_host"]
    
    @rx.var
    def connection_ansible_port_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[1]["ansible_port"]

    # ==== vars for platform validation ===
    @rx.var
    def platform_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.platform_validity(working_platform)[0]
    
    @rx.var
    def platform_instance_name_validity(self)-> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.platform_validity(working_platform)[1]["instance_name"]
    
    @rx.var
    def platform_instance_name_not_in_use(self)-> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.platform_validity(working_platform)[1]["instance_name_not_used"]
    
    @rx.var
    def platform_vip_address_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.platform_validity(working_platform)[1]["vip_address"]
    # === end of platform validation vars ===

    # === vars for instance validation ===
    @rx.var
    def instance_savable(self) -> bool:
        if self.current_uid == "":
            return False
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        else:
            return self.check_instance_savable(working_platform)
    
    @rx.var 
    def instance_uncaught(self) -> bool:
        if self.current_uid == "":
            return False
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        else:
            return self.check_instance_uncaught(working_platform)
    
    @rx.var
    def instance_deployable(self) -> bool:
        if self.current_uid == "":
            return False
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.check_instance_deployable(working_platform)
    # === end of instance validation bars ===

    # Events
    @rx.event
    async def hydrate_state(self):
        # Make sure we have a valid 'blank' agent
        blank_agent = AgentModelView(
                safe_agent={
                    "identity" : "",
                    "source" : "",
                    "config" : "",
                    "config_store": {}
                },
            )
        
        self.list_of_agents = await __agents_off_catalog__()
        platforms_from_api = await __instances_from_api__()
        
        # Ensure we have a blank agent that the user can edit as they so choose
        self.list_of_agents.append(
            blank_agent
        )
        self.platforms.update(platforms_from_api)

    @rx.event(background=True)
    async def delete_temp_uid(self, uid_copy: str):
        import asyncio
        await asyncio.sleep(5)  # Wait for 5 seconds (adjust as needed)
        async with self:
            del self.platforms[uid_copy]
        logger.debug(f"this is the list of param afters: {list(self.platforms.keys())}")

    @rx.event
    def handle_adding_agent(self, agent: AgentModelView):
        working_platform = self.platforms[self.current_uid]

        # Take a copy of the agent we are adding and make sure we dont have an already existing agent of the same identity
        new_agent: AgentModelView = agent.copy()
        if new_agent.identity in working_platform.platform.agents:
            new_agent.identity = f"{new_agent.identity}_{len(list(working_platform.platform.agents.values()))}"
        
        # Set routing id
        new_agent.routing_id = new_agent.identity if new_agent.identity != "" else generate_unique_uid()

        logger.debug("im going to add new component ids for config store...")
        # go through the config store, create new component ids for each config entry
        for i in new_agent.config_store:
            i.component_id = self.generate_unique_uid()
            logger.debug(f"added component uid: {i.component_id}")

        # Set up the safe agent for validation
        new_agent.safe_agent={
                    "identity": new_agent.identity,
                    "source": new_agent.source,
                    "config": new_agent.config,
                    "config_store" : agent.safe_agent["config_store"]
                }
        logger.debug(f"we added: {new_agent.identity}")
        logger.debug(f" and that safe config store is : {new_agent.safe_agent['config_store']}")
        # Prettify its config and config store contents:
        # loop through our agents one more time, and their config store. make if we 
        # encounter a csv file, then we adjust the "Custom" CSV variant
        for config in new_agent.config_store:
            if config.data_type == "CSV":
                logger.debug(f"this is the config: {config}")
                usable_csv = csv_string_to_usable_dict(config.value)
                config.csv_variants["Custom"] = usable_csv
                logger.debug(f"this is the usable csv: {usable_csv}")
            elif config.data_type == "JSON":
                try:
                    json_data = json.loads(config.value)
                    pretty_json = json.dumps(json_data, indent=4)
                    config.value = pretty_json
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON: {e}")
                    pass

        # if config is json
        logger.debug(f"checking if valid json: {check_json(new_agent.config)}")
        pretty_json, success = prettify_json(new_agent.config)
        if success:
            new_agent.config = pretty_json
        for config in new_agent.config_store:
            # im kind of sick of all of this copy and pasting of block of code:
            # TODO find a better and safer way of doing this 
            working_dict = config.csv_variants[config.selected_variant]
            config.csv_header_row = list(working_dict.keys()) 
            config.formatted_csv = [[working_dict[header] for header in config.csv_header_row] for i in range(10)]
            # ==============================================================
            config.safe_entry = config.dict()
            config.uncommitted = False
        working_platform.platform.agents[new_agent.identity] = new_agent
        yield rx.toast.info(f"{'A new agent' if new_agent.identity == '' else f'Agent {new_agent.identity}'} has been added")
        
    @rx.event
    def handle_removing_agent(self, identity: str):
        working_platform = self.platforms[self.current_uid]
        del(working_platform.platform.agents[identity])
        yield rx.toast.info(f"Agent '{identity}' has been removed")

    @rx.event
    def handle_cancel(self):
        working_platform: Instance = self.platforms[self.current_uid]
        
        # Revert back to our previous host entry
        working_platform.host = HostEntryModelView(**working_platform.safe_host_entry)
        working_platform.uncaught = False
        working_platform.valid = working_platform.does_host_have_errors()

        # Revert back to our previous platform
        working_platform.platform.config.instance_name = working_platform.platform.safe_platform["config"].get("instance_name", "volttron1")
        working_platform.platform.config.vip_address = working_platform.platform.safe_platform["config"].get("vip_address", "tcp://127.0.0.1:22916")
        
        # Revert our platform's agents
        for agent in working_platform.platform.agents.values():
            # We revert the addition of agents that haven't been saved/are default. if the user has 
            # added an agent and has saved the agent previously, we have the agent's safe entry so we 
            # don't need to do anything fancy. Basically if the agent has never been saved before, we can revert
            # the addition of the agent. if it has, we dont do anything about it.
            if agent.is_new:
                del(working_platform.platform.agents[agent.identity])


        logger.debug("i pressed cancel,")
        yield rx.toast.info("Changes Reverted.")

    @rx.event
    async def generate_new_platform(self):
        new_uid = self.generate_unique_uid()
        new_host = HostEntryModelView(id="", ansible_user="", ansible_host="")
        new_platform = PlatformModelView(config=PlatformConfigModelView(), in_file=False)
        new_platform.safe_platform = new_platform.to_dict()
        self.platforms[new_uid] = Instance(
                host=new_host, 
                platform=new_platform,
                safe_host_entry=new_host.to_dict()
            )

        yield NavigationState.route_to_platform(new_uid)

    @rx.event
    def copy_platform(self, instance_name: str):
        uid = self.generate_unique_uid()
        copy_instance = deepcopy(self.platforms[instance_name])
        copy_instance.platform.config.instance_name = uid
        copy_instance.refresh_for_copy()
        self.platforms[uid] = copy_instance
        yield NavigationState.route_to_platform(self.platforms[uid].platform.config.instance_name)
        yield rx.toast.info(f"Platform: {instance_name} has been copied")
        # This is a weird way of doing it but we are doing this because 
        # the UI routes to the instance name of a platform. and when we change
        # the instance name after we route to the uid it solves some headaches,
        # but probably should fix the headaches that it would cause.
        copy_instance.platform.config.instance_name = instance_name
        # yield self.update_platform_config_detail("instance_name", instance_name)
        
    @rx.event
    def toggle_advanced(self):
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.advanced_expanded = not working_platform.advanced_expanded
    
    @rx.event
    def toggle_agent_config_details(self):
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.agent_configuration_expanded = not working_platform.agent_configuration_expanded

    @rx.event
    def toggle_web(self):
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.web_checked = not working_platform.web_checked

    @rx.event
    def toggle_federation(self):
        working_platform: Instance = self.platforms[self.current_uid]
        working_platform.federation_checked = not working_platform.federation_checked

    @rx.event
    def update_password_field(self, value: str):
        working_platform_instance = self.platforms[self.current_uid]
        working_platform_instance.password = value

    @rx.event
    def update_detail(self, field: str, value):
        working_platform_instance = self.platforms[self.current_uid]
        if field == "id":
            self._host_resolved = False
            setattr(working_platform_instance.host, "ansible_host", value)
        setattr(working_platform_instance.host, field, value)
        working_platform_instance.uncaught = working_platform_instance.has_uncaught_changes()

    @rx.event
    def update_platform_config_detail(self, field: str, value: str):
        working_platform = self.platforms[self.current_uid]
        if field == "web_bind_address":
            setattr(working_platform, field, value)
        else:
            setattr(working_platform.platform.config, field, value)

    @rx.event
    async def handle_deploy(self):
        working_platform: Instance = self.platforms[self.current_uid]
        try:
            response = await deploy_platform(working_platform.platform.config.instance_name, working_platform.password)
            working_platform.deployed = True
            logger.debug(f"response: {response.json()}")
            yield rx.toast.success("Deployed Successfully!")
        except Exception as e:
            logger.debug(f"there was an error deploying platform {working_platform.platform.config.instance_name}. e: {e}")
            yield rx.toast.error(f"There was an error deploying platform: {working_platform.platform.config.instance_name}")

    @rx.event
    async def handle_save(self):
        working_platform: Instance = self.platforms[self.current_uid]
        uid_copy = deepcopy(self.current_uid)

        logger.debug(f"this is the uid copy: {uid_copy}")
        all_platforms: list[PlatformDefinition] = await get_all_platforms()

        working_platform.safe_host_entry = working_platform.host.to_dict()
        working_platform.uncaught = False
        
        # TODO save the federation field once we have it all up and running
        # federation = working_platform.enable_federation

        # Create base platform
        base_platform_request = CreatePlatformRequest(
            host_id = working_platform.safe_host_entry["id"],
            config=PlatformConfig(
                instance_name=working_platform.platform.config.instance_name,
                vip_address=working_platform.platform.config.vip_address
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
            }
        )

        logger.debug(f"this is the uid copy: {uid_copy}")
        if working_platform.platform.config.instance_name in [p.config.instance_name for p in all_platforms]:
            logger.debug("yes we have committed this already")
            await update_platform(
                working_platform.platform.config.instance_name,
                base_platform_request
            )
            yield rx.toast.success("Changes saved successfully")
            return
        
        host_request = working_platform.host.to_dict()
        host_request["ansible_port"] = int(host_request["ansible_port"])
        host_request["name"] =  working_platform.platform.config.instance_name
        request = CreateOrUpdateHostEntryRequest(**host_request)

        await add_host(request)
        await create_platform(base_platform_request)
        
        # Lets say changes saved successfully and redirect to the new url while deleting our old one
        logger.debug(f"this is the uid copy: {uid_copy}")
        yield rx.toast.success("Changes saved successfully")
        self.platforms[working_platform.platform.config.instance_name] = working_platform
        logger.debug(f"this is the list of params: {list(self.platforms.keys())}")
        yield NavigationState.route_to_platform(working_platform.platform.config.instance_name)
        logger.debug(f"this is the uid about to deletee: {uid_copy}")
        yield PlatformPageState.delete_temp_uid(uid_copy)

    @rx.event
    async def determine_host_reachability(self, working_platform: Instance):
        """On blur of host field, check if the host is reachable"""
        # we have these yield statements scattered because we need make sure when a state var
        # is updated, the app can see it in real time as the function executes. if we dont have it
        # our UI handling the real time spinner will not work as the UI wont be able to read the changed
        # var in real time 
        self._host_pinging = True
        yield
        self._host_resolvable = await self.check_host_reachable(working_platform)
        self._host_pinging = False
        yield
        self._host_resolved = self._host_resolvable
        yield
        return

    # NOTE: i would like to offload the uncaught and valid vars into the state vars because it's easier for the UI to read off of 
    # state vars, for faster development, ive kept these here and i'll change it once it's time to refine the code.
    #   Secondary NOTE: not sure if i've already made changes.
    def handle_uncaught(self, working_platform: Instance):
        working_platform.uncaught = working_platform.has_uncaught_changes()

    def handle_validity(self, working_platform: Instance):
        working_platform.valid = not working_platform.does_host_have_errors()

    def generate_unique_uid(self, length=7) -> str:
        characters = string.ascii_letters + string.digits
        while True:
            new_uid = ''.join(random.choice(characters) for _ in range(length))
            if new_uid not in self.platforms:
                return new_uid
    
    # functions to check if things are savable, reachable, valid, uncaught.
    async def check_host_reachable(self, working_platform: Instance) -> bool:
        host_id = working_platform.host.id
        if host_id =="":
            return False
        response = await ping_resolvable_host(host_id)
        return response.reachable
        
    def check_instance_uncaught(self, working_platform: Instance) -> bool:
        uncaught: bool = False
        # check if host details are changed
        if working_platform.host.to_dict() != working_platform.safe_host_entry:
            uncaught = True

        # check if platform details are changed but skip the agents field as we will handle that separately
        if {k: v for k, v in working_platform.platform.to_dict().items() if k != 'agents'} != {k: v for k, v in working_platform.platform.safe_platform.items() if k != 'agents'}:
            uncaught = True

        # check if we added some new uncaught agents
        for agent in working_platform.platform.agents.values():
            if agent.is_new:
                logger.debug(f"we found an uncaught agent")
                uncaught = True
                # we can break out of this because we just needed to find at least one brand new uncaught agent
                # to render the platform as uncaught
                break
        
        return uncaught

    def check_instance_savable(self, working_platform: Instance) -> bool:
        savable = True

        # manually check the host and all of its stuff...
        host_dict = working_platform.host.to_dict()
        if (
            host_dict["id"] == "" or \
            host_dict["ansible_user"] == "" or \
            host_dict["ansible_port"].isdigit() == False or \
            host_dict["ansible_host"] == "" or \
            self.is_host_resolvable == False or \
            self.host_pinging or \
            self.host_resolved == False
        ):
            logger.debug("Host is not valid...")
            logger.debug(f"Host ID is empty: {host_dict['id'] == ''}")
            logger.debug(f"Ansible user is empty: {host_dict['ansible_user'] == ''}")
            logger.debug(f"Ansible port is not numeric: {host_dict['ansible_port'].isdigit() == False}")
            logger.debug(f"Ansible host is empty: {host_dict['ansible_host'] == ''}")
            logger.debug(f"Host is not resolvable: {self.is_host_resolvable == False}")
            logger.debug(f"Host is currently pinging: {self.host_pinging}")
            logger.debug(f"Host is not resolved: {self.host_resolved == False}")
            logger.debug(f"Here is the host to prove: {host_dict}")
            savable = False

        # check if platform details are valid 
        platform_valid, platform_valid_map = self.platform_validity(working_platform)
        if platform_valid == False:
            savable = False

        return savable

    def check_instance_deployable(self, working_platform: Instance) -> bool:
        return True if self.check_instance_uncaught(working_platform) == False and working_platform.new_instance == False else False

    def connection_validity(self, working_platform: Instance) -> tuple[bool, dict[str, bool]]:
        valid = True
        validity_map: dict[str, bool] = {
            "id" : True,
            "ansible_user" : True,
            "ansible_host" : True,
            "ansible_port" : True,
            "http_proxy" : True,
            "https_proxy" : True,
            "volttron_venv" : True,
            "volttron_home" : True
        }
        # Validate the host id
        if working_platform.host.id == "":
            valid = False
            validity_map["id"] = False

        # Validate the ansible user
        if working_platform.host.ansible_user == "":
            valid = False
            validity_map["ansible_user"] = False

        # Validate the ansible host
        if working_platform.host.ansible_host == "":
            valid = False
            validity_map["ansible_host"] = False

        # Validate the ansible port
        if not isinstance(working_platform.host.ansible_port, int):
            if not working_platform.host.ansible_port.isnumeric():
                valid = False
                validity_map["ansible_port"] = False

        return (valid, validity_map)

    def platform_validity(self, working_platform: Instance) -> tuple[bool, dict[str, bool]]:
        valid = True
        validity_map: dict[str, bool] = {
            "instance_name" : True,
            "instance_name_not_used" : True,
            "vip_address" : True
        }
        # Validate the instance name
        valid_field_name_for_instance = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-/-]*$")
        if not valid_field_name_for_instance.fullmatch(working_platform.platform.config.instance_name):
            valid = False
            validity_map["instance_name"] = False
        
        new_name = working_platform.platform.config.instance_name
        existing_names=[p.platform.safe_platform["config"]["instance_name"] for p in self.in_file_platforms if p.new_instance == False and self.current_uid != p.platform.safe_platform["config"]["instance_name"]]

        # Check to see if our instance is taken already:
        # Seeing if our instance name is inside a list of already registered instance names...
        if working_platform.platform.config.instance_name in [p.platform.safe_platform["config"]["instance_name"] for p in self.in_file_platforms if p.new_instance == False and self.current_uid != p.platform.safe_platform["config"]["instance_name"]]:
            valid = False
            validity_map["instance_name_not_used"] = False
            

        # Validate the tcp address
        if not re.match(r'^tcp://[\d.]+:\d+$', working_platform.platform.config.vip_address):
            valid = False
            validity_map["vip_address"] = False

        return (valid, validity_map)

class AgentConfigState(rx.State):
    working_agent: AgentModelView = AgentModelView()
    selected_component_id: str = ""
    draft_visible: bool = False
    
    # Vars
    # this being named agent details doesn't make sense to be honest
    @rx.var
    def agent_details(self) -> dict:
        args = self.router.page.params
        uid = args.get("uid", "")
        agent_uid = args.get("agent_uid", "")
        return {"uid": uid, "agent_uid": agent_uid}

    @rx.var
    def selected_tab(self) -> str:
        return self.working_agent.selected_agent_config_tab

    # ========= state vars to streamline working checking the validity of working config =======
    
    # TODO: implement def config_uncaught var
    @rx.var
    def path_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity_map["path"]
        return False

    @rx.var
    def config_json_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity_map["json"]
        return False
    
    @rx.var
    def check_csv_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity_map["csv"]
        return False

    @rx.var
    def working_csv_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                if i.data_type == "JSON":
                    return True
                # What we want to do here is to check if 
                valid, csv_string = create_and_validate_csv_string(data_dict=i.csv_variants[i.selected_variant])
                # logger.debug(f"is our cworking csv valid?: {valid}")
                # logger.debug(f"this is our variant: {i.csv_variants[i.selected_variant]}")
                # logger.debug(f"this is our csv string: {csv_string}")
                if valid:
                    i.value = csv_string
                    return True
                return False
            return True
        return True

    @rx.var
    def entry_config_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity_map["config"]
        return False

    @rx.var
    def config_validity(self) -> bool:
        for i in self.working_agent.config_store:
            if i.component_id == self.working_agent.selected_config_component_id:
                working_config = i
                validity, validity_map= self.check_entry_validity(working_config)
                return validity
        return False

    @rx.var
    def changed_configs_list(self) -> list[str]:
        """returns a list of component ids for the config store entries that have been changed"""
        return list(config.component_id for config in self.working_agent.config_store if config.dict() != config.safe_entry or config.safe_entry["path"] == "")
    
    @rx.var
    def committed_configs(self) -> list[ConfigStoreEntryModelView]:
        return [
            ConfigStoreEntryModelView(
                    path=config.safe_entry["path"], 
                    data_type=config.safe_entry["data_type"],
                    value=config.safe_entry["value"],
                    csv_variants=config.csv_variants,
                    component_id=config.component_id,
                    selected_variant=config.selected_variant,
                ) for config in self.working_agent.config_store if not config.uncommitted]
    
    @rx.var
    def has_valid_configs(self) -> bool:
        return (len(self.working_agent.config_store) > 0 and 
                any(not config.uncommitted for config in self.working_agent.config_store))

    @rx.var
    def num_of_new_invalid_configs(self) -> int:
        return len([config.path for config in self.working_agent.config_store if config.uncommitted]) 
    # ======== End of config validation vars =========


    # ======= state vars to streamline agent validation =======
    @rx.var
    async def agent_valid(self) -> bool:
        """checks if the agent identity is valid"""
        valid, validity_map = await self.check_agent_validity()
        return valid
    
    @rx.var
    async def agent_identity_not_in_use(self) -> bool:
        """checks if the agent identity is valid"""
        valid, validity_map = await self.check_agent_validity()
        return validity_map["identity_not_in_use"]

    @rx.var
    async def agent_identity_validity(self) -> bool:
        """checks if the agent identity is valid"""
        valid, validity_map = await self.check_agent_validity()
        return validity_map["identity_valid"]
    
    @rx.var
    async def agent_source_validity(self) -> bool:
        """checks if the agent source is valid"""
        valid, validity_map = await self.check_agent_validity()
        return validity_map["source"]
    
    @rx.var
    async def agent_config_validity(self) -> bool:
        """checks if the agent config is valid"""
        valid, validity_map = await self.check_agent_validity()
        return validity_map["config"]

    # ======== End of agent validation vars========

    # Events
    @rx.event
    async def hydrate_working_agent(self):
        """Initialize working agent from platform state"""
        platform_state: PlatformPageState = await self.get_state(PlatformPageState)
        working_platform: Instance = platform_state.platforms[self.agent_details["uid"]]
        
        # Find agent by routing_id
        for agent in working_platform.platform.agents.values():
            if agent.routing_id == self.agent_details["agent_uid"]:
                self.working_agent = agent
                break

    @rx.event
    def change_agent_config_tab(self, value):
        self.working_agent.selected_agent_config_tab = value

    @rx.event
    def flip_draft_visibility(self):
        self.draft_visible = not self.draft_visible
        logger.debug(f"ok bro is {self.draft_visible}")
        logger.debug(f"this is our working agent config store: {self.working_agent.config_store}")
        logger.debug(f"committed configs in agent config store: {self.committed_configs}")

    @rx.event
    async def update_agent_detail(self, field: str, value: str, id: str = None):
        """Update agent details directly"""
        setattr(self.working_agent, field, value)
        
        if id is not None:
            yield rx.set_value(id, value)

        valid, validity_map = await self.check_agent_validity()
        self.working_agent.contains_errors = not valid

    @rx.event
    async def update_config_detail(self, field: str, value: str, id: str = None):
        """Update a config store entry directly"""
        for config in self.working_agent.config_store:
            # get the working config
            if config.component_id == self.working_agent.selected_config_component_id:
                logger.debug("updating details...")
                
                if field == "data_type":
                    # if the config value is nothing, just let them change the data type mannn
                    if config.value == "":
                        setattr(config, field, value)
                    else:
                        # method to convert if json to csv and vice versa
                        format =  identify_string_format(config.value) 
                        # Means we are switching from CSV -> JSON
                        if format == "CSV":
                            json_string =  csv_string_to_json_string(config.value)
                            setattr(config, field, value)
                            setattr(config, "value", json_string)
                        elif format == "JSON":
                            csv_string =  json_string_to_csv_string(config.value)
                            usable_csv =  csv_string_to_usable_dict(csv_string)
                            config.csv_variants["Custom"] = usable_csv
                            setattr(config, field, value)
                else:
                    setattr(config, field, value)
                valid, valid_map = self.check_entry_validity(config)
                logger.debug(f"this is the validity map: {valid_map}")
                config.valid = valid
                config.changed = config.dict() != config.safe_entry
                if id is not None:
                    yield rx.set_value(id, value)
                break
    
    @rx.event
    def handle_unsaved_config_banner_click(self, component_id: str):
        """Handle click on unsaved config banner to set the selected component id"""
        self.working_agent.selected_config_component_id = component_id
        yield AgentConfigState.flip_draft_visibility
        yield AgentConfigState.change_agent_config_tab("2")

    @rx.event
    async def handle_config_store_entry_upload(self, files: list[rx.UploadFile]):
        # dealing with file uploads
        current_file = files[0]
        upload_data = await current_file.read()
        outfile = (rx.get_upload_dir() / current_file.name)
        
        with outfile.open("wb") as file_object:
            file_object.write(upload_data)

        result: str = ""
        file_type: str = ""

        if current_file.name.endswith('.json'):
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                file_type = "JSON"
                result = json.dumps(data, indent=4)

        elif current_file.name.endswith('.csv'):
            with open(outfile, 'r') as file_object:
                reader = csv.reader(file_object)
                output = io.StringIO()
                writer = csv.writer(output)
                for row in reader:
                    writer.writerow(row)
                file_type="CSV"
                result = output.getvalue()
                output.close()
        else:
            yield rx.toast.error("Unsupported file format")
            return
        
        # creating a model view from our uploaded config
        agent = self.working_agent
        new_config_entry= ConfigStoreEntryModelView(
                path="",
                data_type=file_type,
                value=result,
                component_id=generate_unique_uid()
            )
        if file_type == "CSV":
            usable_csv = csv_string_to_usable_dict(result)
            logger.debug(f"this is the usable? csv: {usable_csv}")
            new_config_entry.csv_variants["Custom"] = usable_csv
            logger.debug(f"this is out variants: {new_config_entry.csv_variants}")

        new_config_entry.safe_entry=new_config_entry.dict()
        logger.debug(f"I submitted a safe entry: {new_config_entry.safe_entry}")
        logger.debug(f"pls add: {new_config_entry.component_id}")
        agent.config_store.append(
            new_config_entry
        )
        logger.debug("agent config store entry was uploaded")
        yield AgentConfigState.set_component_id(new_config_entry.component_id)
        yield rx.toast.success("Config store entry uploaded successfully")
        delete_file.delete_file(current_file.name)

    @rx.event
    async def handle_agent_config_upload(self, files: list[rx.UploadFile]):
        file = files[0]
        upload_data = await file.read()
        outfile = (rx.get_upload_dir() / file.name)
        
        with outfile.open("wb") as file_object:
            file_object.write(upload_data)

        result: str = ""

        if file.name.endswith('.json'):
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                result = json.dumps(data, indent=4)
        elif file.name.endswith('.yaml') or file.name.endswith('.yml'):
            with open(outfile, 'r') as file_object:
                data = yaml.safe_load(file_object)
                result = yaml.dump(data, sort_keys=False, default_flow_style=False)
        else:
            yield rx.toast.error("Unsupported file format")
            return

        agent = self.working_agent
        agent.config = result
        yield rx.set_value("agent_config_field", result)
        delete_file.delete_file(file.name)
    
    @rx.event
    def create_blank_config_entry(self):
        agent = self.working_agent
        new_component_id = generate_unique_uid()
        blank_config = ConfigStoreEntryModelView(
                path="",
                data_type="JSON",
                value="",
                component_id=new_component_id,
                safe_entry={
                    "path" : "",
                    "data_type" : "JSON",
                    "value" : ""
                }
            )
        blank_config.safe_entry = blank_config.dict()
        agent.config_store.append(blank_config)
        yield AgentConfigState.set_component_id(new_component_id)

    @rx.event
    def save_config_store_entry(self, config: ConfigStoreEntryModelView):
        # Keep a variable so we can stack the toast errors if config entry has many errors, instead of ending
        # the function at just one error
        import re
        committable: bool = True
        
        logger.debug(f"this is our config's safe entry: {[entry.safe_entry for entry in self.working_agent.config_store]}")
        list_of_config_paths: list[tuple[str, str]] = [
            (entry.safe_entry["path"], entry.component_id) for entry in self.working_agent.config_store
        ]
        logger.debug(f"list of config paths: {list_of_config_paths}")
        
        # Check if the path exists and belongs to a different component
        for path, component_id in list_of_config_paths:
            if config.path == "" or (config.path == path and config.component_id != component_id):
                # This check catches all empty paths or duplicate paths
                committable = False
                yield rx.toast.error(f"Config path is already in use.")

        # Validate the path format using a stricter regex pattern
        # valid_field_name_for_config_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
        # if not valid_field_name_for_config_pattern.fullmatch(config.path):
        #     committable = False
        #     yield rx.toast.error("Path must start with a letter and can only contain letters, numbers, underscores, or hyphens.")
            
        if config.data_type == "CSV" and committable:
            try:
                logger.debug(f"just for notes, here is thing: {config.csv_variants}")
                working_dict = config.csv_variants[config.selected_variant]
                headers=list(working_dict.keys())
                rows = [[working_dict[header] for header in headers] for i in range(10)]
                
                csv_string = create_csv_string(headers, rows)
                
                if not check_csv(csv_string):
                    raise ValueError("CSV String is not valid")

                config.csv_header_row=headers
                config.formatted_csv=rows
            except Exception as e:
                logger.debug(f"error: {e}")
                committable = False
                yield rx.toast.error("CSV variant is not valid")
            pass

        elif config.data_type =="JSON" and committable:
            if check_json(config.value) == False:
                committable = False
                yield rx.toast.error("Inputted JSON is not valid")
        
        if committable == False:
            return
        
        config.safe_entry = config.dict()
        config.uncommitted=False

        # Find and update the entry in the config_store just to be safe
        for i, entry in enumerate(self.working_agent.config_store):
            if entry.component_id == config.component_id:
                # logger.debug(f"ok first of all, uncommitted??: {self.working_agent.config_store[i].uncommitted}")
                self.working_agent.config_store[i] = config
                # logger.debug(f"updated entries committed state: {self.working_agent.config_store[i].uncommitted}")
                break

        # logger.debug(f"our agent after entry save: {self.working_agent}")
        return rx.toast.success("Config saved successfully")

    @rx.event
    def delete_config_store_entry(self, config: ConfigStoreEntryModelView):
        logger.debug(f"implement the rest of this, {config.component_id} was clicked for deletion")
        for index, entry in enumerate(self.working_agent.config_store):
            if entry.component_id == config.component_id:
                self.working_agent.config_store.pop(index)
                logger.debug(f"selected_component_id = {self.selected_component_id}, entry.component_id = {config.component_id}")
                if self.selected_component_id == config.component_id:
                    yield AgentConfigState.set_component_id("")
                yield rx.toast.info(f"Config store entry has been removed.")
                return

    @rx.event
    def text_editor_edit(self, config: ConfigStoreEntryModelView, value: str):
        logger.debug("im being ran right?")
        config.value = value
        config.valid = check_json(config.value)
        logger.debug(f"valid?: {config.valid}")
        logger.debug(f" bruhhh this odddeee: {self.has_valid_configs}")

    @rx.event
    async def save_agent_config(self):
        """Save agent configuration"""
        agent = self.working_agent
        # check if identity already exists:
        platform_state: PlatformPageState = await self.get_state(PlatformPageState)
        working_platform: Instance = platform_state.platforms[self.agent_details["uid"]]
        registered_identities: list[str] = [ i for i, a in working_platform.platform.agents.items() if a.routing_id != agent.routing_id]
        if agent.identity in registered_identities:
            yield AgentConfigState.flip_draft_visibility
            yield rx.toast.error("Identity is already in use!")
            return
        agent.is_new = False
        agent.safe_agent = agent.to_dict()

        # Work with our safe agent just to be safe
        # working_platform.platform.safe_platform["agents"][agent.safe_agent["identity"]] = agent.safe_agent
        logger.debug("oh yeah, we saved and here is our platform agents:")
        logger.debug(f"{working_platform.platform.agents}")
        yield AgentConfigState.flip_draft_visibility
        yield rx.toast.success("Agent configuration saved")

    @rx.event
    def print_config_properties(self, config: ConfigStoreEntryModelView):
        unpacked = config.dict()
        logger.debug(f"here is my config: \n {unpacked}")
        logger.debug("this is a component id ")
        logger.debug(config.component_id)

    @rx.event
    def set_component_id(self, component_id: str):
        if self.working_agent.selected_config_component_id == component_id:
            self.working_agent.selected_config_component_id = ""
        else:
            self.working_agent.selected_config_component_id = component_id
        logger.debug(f"our new config entry: {self.working_agent.selected_config_component_id}")

    async def check_agent_validity(self) -> tuple[bool, dict[str, bool]]:
        valid: bool = True
        validity_map: dict[str, bool] = {
            "identity_valid": True,
            "identity_not_in_use": True,
            "source": True,
            "config": True
        }

        platform_state: PlatformPageState = await self.get_state(PlatformPageState)
        if self.agent_details["uid"] == "":
            return (valid, validity_map)
        
        working_platform: Instance = platform_state.platforms[self.agent_details["uid"]]
        

        
        # Create a dictionary mapping identities to routing IDs
        identity_to_rid = {identity: agent.routing_id 
                        for identity, agent in working_platform.platform.agents.items()}

        # Check if the identity already exists
        if self.working_agent.identity in identity_to_rid:
            # Checking if the existing identity is not the same as the current agent's identity via routing id
            if self.working_agent.routing_id != identity_to_rid[self.working_agent.identity]:
                valid = False
                validity_map["identity_not_in_use"] = False

        # implement Source validity:
        if check_path(self.working_agent.source) == False:
            valid = False
            validity_map["source"] = False
        
        # implement Identity validity:
        if check_regular_expression(self.working_agent.identity) == False:
            valid = False
            validity_map["identity_valid"] = False

        # config validity:
        # verify if the config is valid json or yaml
        if check_json(self.working_agent.config) == False:
            if check_yaml(self.working_agent.config) == False or self.working_agent.config == "":
                validity_map["config"] = False
                valid = False
        
        # try:
        #     # First try to parse as JSON
        #     import json
        #     json.loads(self.working_agent.config)
        #     config_valid = True
        # except json.JSONDecodeError:
        #     try:
        #         # If JSON fails, try to parse as YAML
        #         import yaml
        #         yaml.safe_load(self.working_agent.config)
        #         config_valid = True
        #     except yaml.YAMLError:
        #         # Config is neither valid JSON nor valid YAML
        #         pass
        
        # if not config_valid:
        #     valid = False
        #     validity_map["config"] = False
        # logger.debug(f"this is our validity: {valid} and here is our map: {validity_map}")
        return (valid, validity_map)

    def check_entry_validity(self, config: ConfigStoreEntryModelView) -> tuple[bool, dict[str, bool]]:
        """checks the validity of each field in the config. also checks the json/csv versions
        returns bool for overall validity, and dict containing fields with errors in a string bool value pair"""
        valid: bool = True
        config_fields: dict[str, bool] = {
            "path" : True,
            "csv" : True,
            "json" : True,
            "config": True
        }

        # Checking validity for each data type
        if config.data_type == "JSON":
            config_fields["json"] = check_json(config.value)
            if check_json(config.value) == False:
                valid = False
                config_fields["config"] = False

            # add a separate base case for if the json is just an empty string
            if config.value == "":
                valid=False
                # This will let the user just be able to switch to csv if its a new empty
                # config store entry
                config_fields["config"] = True  
        else:
            # if else, we validate the csv_field
            try:
                # get selected variant and turn it into legible csv
                working_dict = config.csv_variants[config.selected_variant]
                headers=list(working_dict.keys())
                rows = [working_dict[header] for header in headers]
                
                csv_string = create_csv_string(headers, rows)
                if check_csv(csv_string):
                    raise ValueError()
                
            except Exception as e:
                valid = False
                config_fields["csv"] = False
                config_fields["config"] = False
                logger.debug(f"the working csv field is not valid")
        
        # Validate the path format to include periods
        valid_field_name_for_config_path = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-/-]*$")
        if not valid_field_name_for_config_path.fullmatch(config.path):
            valid = False
            config_fields["path"] = False

        if self.working_csv_validity == False:
            valid = False
            config_fields["csv"] = False

        return (valid, config_fields)

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



class BacnetScanState(rx.State):
    selected_property_tab: Literal["read", "write"] = "read"  # Default to "read" tab
    discovered_devices: list[BACnetDeviceModelView] = []  # Store discovered devices
    selected_device: BACnetDeviceModelView | None = None  # Store the currently selected device
    ip_detection_mode: Literal["", "local_ip", "windows_host_ip"] = ""  # "local_ip", "windows_host_ip" or ""
    expanded_device_index: int = -1

    scanning_bacnet_range: bool = False
    is_starting_proxy: bool = False
    proxy_up: bool = False
    pinging_ip: bool = False
    _is_write_property_valid: bool = False
    _is_read_property_valid: bool = False
    _warn_ping_range: bool = False
    
    # Fields
    proxy_field_value: str = ""

    # Models
    request_who_is: RequestWhoIsModel = RequestWhoIsModel()
    read_device_all: ReadDeviceAllModel = ReadDeviceAllModel()
    scan_ip_range: ScanIPRangeModel = ScanIPRangeModel()
    ping_ip: PingIPModel = PingIPModel()
    read_property: ReadPropertyModel = ReadPropertyModel()
    write_property: WritePropertyModel = WritePropertyModel()

    # UI driven models
    local_ip_info: LocalIPModel = LocalIPModel()
    windows_host_ip_info: WindowsHostIPModel = WindowsHostIPModel()

    # For bacnet point stuff
    writable_map = {
        0: False,  # analog-input
        1: True,   # analog-output
        2: False,  # analog-value (temporarily set to False, but these are typically writable)
        3: False,  # binary-input
        4: True,   # binary-output
        5: False,  # binary-value (temporarily set to False, but these are typically writable)
        6: True,   # calendar
        7: True,   # command
        8: False,  # device
        9: True,   # event-enrollment
        10: True,  # file
        11: True,  # group
        12: True,  # loop
        13: False, # multi-state-input
        14: True,  # multi-state-output
        15: True,  # notification-class
        16: True,  # program
        17: True,  # schedule
        18: False, # averaging
        19: False, # multi-state-value (temporarily set to False, but these are typically writable)
        20: False, # trend-log
        21: False, # life-safety-point
        22: False, # life-safety-zone
        23: False, # accumulator
        24: False, # pulse-converter
        25: False, # event-log
        26: True,  # global-group
        27: False, # trend-log-multiple
        28: True,  # load-control
        29: False, # structured-view
        30: True,  # access-door
        31: False, # unassigned
        32: False, # access-credential
        33: False, # access-point
        34: True,  # access-rights
        35: False, # access-user
        36: False, # access-zone
        37: False, # credentional-data-input
        38: False, # network-security (removed)
        39: False, # bitstring-value (temporarily set to False, but these are typically writable)
        40: False, # characterstring-value (temporarily set to False, but these are typically writable)
        41: False, # date-pattern-value (temporarily set to False, but these are typically writable)
        42: False, # date-value (temporarily set to False, but these are typically writable)
        43: False, # datetime-pattern-value (temporarily set to False, but these are typically writable)
        44: False, # datetime-value (temporarily set to False, but these are typically writable)
        45: False, # integer-value (temporarily set to False, but these are typically writable)
        46: False, # large-analog-value (temporarily set to False, but these are typically writable)
        47: False, # octetstring-value (temporarily set to False, but these are typically writable)
        48: False, # positive-integer-value (temporarily set to False, but these are typically writable)
        49: False, # time-pattern-value (temporarily set to False, but these are typically writable)
        50: False, # time-value (temporarily set to False, but these are typically writable)
        51: True,  # notification-forwarder
        52: True,  # alert-enrollment
        53: True,  # channel
        54: True,  # lighting-output
    }

    # important event, actually spins up the tool when the page loads.
    @rx.event
    async def start_tool(self, value):
        await start_tool(
            ToolRequest(
                tool_name=value,
                module_path="bacnet_scan_tool.main:app",
                use_poetry=False
            )
        )


    # Computed Vars
    @rx.var
    def warn_ping_range(self) -> bool: 
        self._warn_ping_range = "/" in self.scan_ip_range.network_string
        return self._warn_ping_range

    @rx.var
    def has_devices(self) -> bool:
        """Check if any devices have been discovered."""
        return len(self.discovered_devices) > 0
    
    @rx.var
    def is_read_property_valid(self) -> bool:
        for field, value in self.read_property.model_dump().items():
            if field == "property_array_index":
                break
            if value == "":
                self._is_read_property_valid = False
                return self._is_read_property_valid
        self._is_read_property_valid = True
        return self._is_read_property_valid

    @rx.var
    def is_write_property_valid(self) -> bool:
        for field, value in self.write_property.model_dump().items():
            if field == "property_array_index":
                break
            if value == "":
                self._is_write_property_valid = False
                return self._is_write_property_valid
        self._is_write_property_valid = True
        return self._is_write_property_valid

    @rx.var
    def selected_points(self) -> list[BACnetDevicePointModelView]:
        if self.selected_device is not None:
            return [point for point in self.selected_device.points]
        return []
    
    # Events
    @rx.event
    def toggle_select_all_points(self, checked: bool):
        self.selected_device.select_all_points = checked
        for point in self.selected_device.points:
            point.selected=checked

    @rx.event
    def handle_device_check(self, device_index: int, checked: bool):
        self.selected_device.select_all_points = False
        self.selected_device.points[device_index].selected = checked

    @rx.event
    def handle_proxy_field_edit(self, value: str):
        self.proxy_field_value = value 

    @rx.event
    def set_selected_property_tab(self, tab: str):
        """Update the selected property tab."""
        self.selected_property_tab = tab
    
    @rx.event
    def handle_device_row_click(self, device_index: int):
        """Handle when a device row is clicked."""
        if 0 <= device_index < len(self.discovered_devices):
            selected_device = self.discovered_devices[device_index]
            if selected_device == self.selected_device:
                self.selected_device = None
                return
            self.selected_device = selected_device
            
            # Auto-fill the property operation fields with selected device info
            device_address = selected_device.scanned_ip_target
            device_id = selected_device.deviceIdentifier
            
            # Update read property form
            self.read_property.device_address = device_address
            self.read_property.object_identifier = f"{device_id}"
            
            # Update write property form
            self.write_property.device_address = device_address
            self.write_property.object_identifier = f"{device_id}"
            
            yield rx.toast.info(f"Selected device: {selected_device.object_name}")
    
    @rx.event
    def set_ip_detection_mode(self, mode: Literal["windows_host_ip", "local_ip"]):
        """Switch between local IP and Windows host IP mode."""
        self.ip_detection_mode = mode
        yield BacnetScanState.get_network_info()

    @rx.event
    async def get_network_info(self):
        """Get network information based on current detection mode."""
        self.pinging_ip = True
        yield rx.toast.info(f"Retrieving network information...")        
        if self.ip_detection_mode == "local_ip":
            yield BacnetScanState.handle_get_local_ip()
        else:
            yield BacnetScanState.handle_get_windows_host_ip()

        self.pinging_ip = False
        yield

    @rx.event
    def set_open_items(self, value):
        self._open_accordion_items = value

    @rx.event
    def toggle_proxy(self):
        """Toggle the proxy state"""
        if self.proxy_up:
            yield BacnetScanState.stop_proxy()
        else:
            yield rx.toast.info("Starting proxy...")
            yield BacnetScanState.start_proxy()

    @rx.event
    async def start_proxy(self):
        """Handle the start proxy button click"""
        if self.is_starting_proxy:
            yield rx.toast.info("Proxy is already starting.")
            return
        self.is_starting_proxy = True
        yield
        try:
            ip_address = self.proxy_field_value if self.proxy_field_value != "" else None
            logger.debug(f"this is the ip address we will start a proxy with: {ip_address}")
            data = await start_bacnet_proxy(ip_address)
            if data.get("status") == "error":
                raise Exception(data)
            self.proxy_field_value = data["address"]
            self.proxy_up = True
            self.is_starting_proxy = False
            yield rx.toast.success("Proxy started successfully.")
        except Exception as e:
            logger.debug(e)
            self.is_starting_proxy = False
            yield rx.toast.error("There was an error starting up a BACnet proxy")

    @rx.event
    async def stop_proxy(self):
        try:
            await stop_bacnet_proxy()
            self.proxy_up = False
            yield rx.toast.success("Proxy stopped successfully")
        except Exception as e:
            logger.debug(f"Error starting proxy: {e}")
            yield rx.toast.error("There was an error stopping the BACnet proxy")
    
    @rx.event
    async def handle_bacnet_scan(self):
        """Handle the BACnet scan button click"""
        if self.scanning_bacnet_range:
            yield rx.toast.info("BACnet scan is already in progress.")
            return
        self.scanning_bacnet_range = True
        yield
        # TODO implement scan logic
        import asyncio
        await asyncio.sleep(2)
        self.scanning_bacnet_range = False
        self.discovered_devices=[
            {"name": "Device Alpha", "id": "1234", "address": "192.168.1.10"},
            {"name": "Device Beta", "id": "5678", "address": "192.168.1.12"},
            {"name": "Device Gamma", "id": "9012", "address": "192.168.1.14"},
        ]
        yield

    # Handle inputs into model
    @rx.event
    def request_who_is_input(self, field: str, value: str):
        """Handle input changes for the Request Who Is form."""
        if field == "device_instance_low":
            self.request_who_is.device_instance_low = value
        elif field == "device_instance_high":
            self.request_who_is.device_instance_high = value
        elif field == "dest":
            self.request_who_is.dest = value

    @rx.event
    def read_device_all_input(self, field: str, value: str):
        """Handle input changes for the Read Device All form."""
        if field == "device_address":
            self.read_device_all.device_address = value
        elif field == "device_object_identifier":
            self.read_device_all.device_object_identifier = value

    @rx.event
    def scan_ip_range_input(self, value: str):
        """Handle input changes for the Scan IP Range form."""
        self.scan_ip_range.network_string = value

    @rx.event
    def ping_ip_input(self, value: str):
        """Handle input changes for the Ping IP form."""
        self.ping_ip.ip_address = value

    @rx.event
    def read_property_input(self, field: str, value: str):
        """Handle input changes for the Read Property form."""
        if field == "device_address":
            self.read_property.device_address = value
        elif field == "object_identifier":
            self.read_property.object_identifier = value
        elif field == "property_identifier":
            self.read_property.property_identifier = value
        elif field == "property_array_index":
            # Handle empty string as None for optional field
            self.read_property.property_array_index = value if value.strip() else None

    @rx.event
    def write_property_input(self, field: str, value: str):
        """Handle input changes for the Write Property form."""
        if field == "device_address":
            self.write_property.device_address = value
        elif field == "object_identifier":
            self.write_property.object_identifier = value
        elif field == "property_identifier":
            self.write_property.property_identifier = value
        elif field == "value":
            self.write_property.value = value
        elif field == "priority":
            self.write_property.priority = value
        elif field == "property_array_index":
            # Handle empty string as None for optional field
            self.write_property.property_array_index = value if value.strip() else None

    @rx.event
    def ip_address_input(self, value: str):
        """Handle input change for the main IP address field."""
        self.ip_address = value


    # Handle the actual endpoint actions/functionality
    @rx.event
    async def handle_request_who_is(self):
        """Handle the Request Who Is form submission."""
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return
            
        # Access form data using self.request_who_is.device_instance_low, etc.
        yield rx.toast.info(f"Sending Who-Is request from {self.request_who_is.device_instance_low} to {self.request_who_is.device_instance_high}")
        
        # TODO: Implement actual BACnet logic here
        import asyncio
        await asyncio.sleep(1)
        
        # Example response handling
        yield rx.toast.success("Who-Is request completed.")
    
    @rx.event
    async def handle_read_device_all(self):
        """Handle the Read Device All form submission."""
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return
            
        yield rx.toast.info(f"Reading all properties from device {self.read_device_all.device_address}")
        
        # TODO: Implement actual BACnet logic here
        import asyncio
        await asyncio.sleep(1)
        
        yield rx.toast.success("Read Device All completed.")
    
    @rx.event
    async def handle_scan_ip_range(self):
        """Handle the Scan IP Range form submission."""
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return
        self.scanning_bacnet_range = True
        yield rx.toast.info(f"Scanning network: {self.scan_ip_range.network_string}")
        
        try:
            scan_results: BACnetScanResults = await scan_bacnet_ip_range(self.scan_ip_range.network_string)
            
            # Get devices 
            devices = [
                BACnetDeviceModelView(
                **device.model_dump(),
                ) for device in scan_results.devices
            ]

            # Read device all on each of our devices[]
            for device in devices:
                logger.debug(f"this is our device we are operating on: {device}")

                try:            
                    res = await read_bacnet_device_all(
                            BACnetReadDeviceAllRequest(
                                device_address=device.scanned_ip_target,
                                device_object_identifier=device.deviceIdentifier
                            )
                        )
                    if res.get("status") == "error":
                        logger.debug(f"this is our res: {res}")
                        raise Exception(f"Error occured calling api though thin endpoint wrapper")
                except Exception as e:
                    import traceback
                    logger.debug(f"An error occured running scan: {traceback.format_exc()}")
                    break

                points: list = res["properties"]["object-list"]
                logger.debug(f"we are going to go through {len(points) - 1}")
                logger.debug(f"sike we only getting 50")
                # go through each object-list item, skip the first one which is ours, then read property the stuff
                for obj in points[1:21]:
                    logger.debug(f"Processing object: {obj}")
                    
                    object_identifier: str = f"{obj[0]},{obj[1]}"
                    logger.debug(f"Created object_identifier: {object_identifier}")
                    
                    writable: bool = self.writable_map[obj[0]]
                    logger.debug(f"Object type {obj[0]} is writable: {writable}")
                    
                    # Getting point name
                    logger.debug(f"Step 1: Getting point name for {object_identifier} at {device.scanned_ip_target}")
                    point_name_response = await read_bacnet_property(
                        BACnetReadPropertyRequest(
                            device_address=device.scanned_ip_target,
                            object_identifier=object_identifier,
                            property_identifier="object-name"
                        )
                    )
                    logger.debug(f"Point name response received: {point_name_response}")
                    point_name = point_name_response["result"]["_value"]
                    logger.debug(f"Point name extracted: {point_name}")
                    
                    # Getting units
                    logger.debug(f"Step 2: Getting units for {object_identifier} at {device.scanned_ip_target}")
                    try:
                        units_response = await read_bacnet_property(
                            BACnetReadPropertyRequest(
                                device_address=device.scanned_ip_target,
                                object_identifier=object_identifier,
                                property_identifier="units"
                            )
                        )
                        logger.debug(f"Units response received: {units_response}")
                        units = units_response["result"]["_value"]
                        logger.debug(f"Units extracted: {units}")
                    except Exception as e:
                        logger.error(f"Failed to get units: {e}")
                        units = "unknown"
                        logger.debug(f"Using default units: {units}")
                    
                    # Getting present value
                    logger.debug(f"Step 3: Getting present value for {object_identifier} at {device.scanned_ip_target}")
                    try:
                        present_value_response = await read_bacnet_property(
                            BACnetReadPropertyRequest(
                                device_address=device.scanned_ip_target,
                                object_identifier=object_identifier,
                                property_identifier="present-value"
                            )
                        )
                        logger.debug(f"Present value response received: {present_value_response}")
                        present_value = present_value_response["result"]["_value"]
                        logger.debug(f"Present value extracted: {present_value}")
                    except Exception as e:
                        logger.error(f"Failed to get present value: {e}")
                        present_value = "N/A"
                        logger.debug(f"Using default present value: {present_value}")
                    
                    # Getting Notes
                    logger.debug(f"Step 4: Getting notes for {object_identifier} at {device.scanned_ip_target}")
                    try:
                        notes_value_response = await read_bacnet_property(
                            BACnetReadPropertyRequest(
                                device_address=device.scanned_ip_target,
                                object_identifier=object_identifier,
                                property_identifier="notes"
                            ),
                            timeout=4.0
                        )
                        logger.debug(f"Notes value response received: {notes_value_response}")
                        notes_value = notes_value_response["result"]["_value"]
                        logger.debug(f"Notes value extracted: {notes_value}")
                    except Exception as e:
                        logger.error(f"Failed to get notes value: {e}")
                        notes_value = "N/A"
                        logger.debug(f"Using default notes value: {notes_value}")

                    # Create and add the point to device
                    logger.debug(f"Step 5: Creating point model for {point_name}")
                    point = BACnetDevicePointModelView(
                        device_name=point_name,
                        writable=writable,
                        present_value=present_value,
                        units=units,
                        notes=notes_value
                    )
                    logger.debug(f"Point created: {point}")
                    
                    logger.debug(f"Step 5: Adding point to device {device}")
                    device.points.append(point)
                    logger.debug(f"Point added to device successfully. Device now has {len(device.points)} points.")

            logger.debug(f"this is our scan results: {scan_results}")
            self.discovered_devices = devices
            yield rx.toast.success("IP Range scan completed.")
        except:
            import traceback
            logger.debug(f"An error occured running scan: {traceback.format_exc()}")
        
        self.scanning_bacnet_range = False
    
    @rx.event
    async def handle_ping_ip(self):
        """Handle the Ping IP form submission."""
        yield rx.toast.info(f"Pinging IP: {self.ping_ip.ip_address}")
        
        # TODO: Implement actual ping logic here
        import asyncio
        await asyncio.sleep(0.5)
        
        yield rx.toast.success("Ping completed.")
    
    @rx.event
    async def handle_read_property(self):
        """Handle the Read Property form submission."""
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return
            
        yield rx.toast.info(f"Reading property from {self.read_property.device_address}")
        
        # TODO: Implement actual BACnet logic here
        import asyncio
        await asyncio.sleep(1)
        
        yield rx.toast.success("Read Property completed.")
    
    @rx.event
    async def handle_write_property(self):
        """Handle the Write Property form submission."""
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return
            
        yield rx.toast.info(f"Writing to property on {self.write_property.device_address}")
        
        # TODO: Implement actual BACnet write logic here
        import asyncio
        await asyncio.sleep(1)
        
        yield rx.toast.success("Write Property completed.")

    @rx.event
    async def handle_get_local_ip(self):
        try:
            self.local_ip_info = await get_bacnet_local_ip(self.local_ip_info)
            self.scan_ip_range.network_string = self.local_ip_info.cidr
            yield rx.toast.success("Retrieved Local Host IP")
        except Exception as e:
            logger.debug(f"There was an error getting local ip info {e}")

    @rx.event
    async def handle_get_windows_host_ip(self):
        try:
            self.windows_host_ip_info = await get_windows_host_ip()
            self.scan_ip_range.network_string = self.windows_host_ip_info.windows_host_ip.rsplit('.', 1)[0] + ".0/24" # Split at the last period, max 1 split. tack it off with cidr range
            yield rx.toast.success("Retrieved Host IP")
        except Exception as e:
            logger.debug(f"There was an error getting local ip info {e}")
