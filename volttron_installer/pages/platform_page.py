import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.tiles import config_tile
from ..components.buttons import icon_button_wrapper
from ..components.header.header import header
from ..components.buttons.tile_icon import tile_icon
from ..navigation.state import NavigationState
from ..components.form_components import form_entry
from ..backend.models import AgentType, HostEntry, PlatformConfig, PlatformDefinition, ConfigStoreEntry, AgentDefinition
from typing import List, Dict, Literal
from ..backend.endpoints import get_all_platforms, create_platform, \
    CreatePlatformRequest, CreateOrUpdateHostEntryRequest, add_host, \
    get_agent_catalog, get_hosts, update_platform, get_inventory_service, \
    get_platform_service, get_platform_status, deploy_platform, \
    get_ansible_service
from ..functions.create_component_uid import generate_unique_uid
from ..functions.conversion_methods import csv_string_to_usable_dict
from ..functions.validate_content import check_json
from ..functions.prettify import prettify_json
from loguru import logger
from ..model_views import HostEntryModelView, PlatformModelView, AgentModelView, ConfigStoreEntryModelView, PlatformConfigModelView
from ..thin_endpoint_wrappers import *
import string, random, json, csv, yaml, re
from copy import deepcopy

parts = Literal["connection", "instance_configuration"]
 
class Instance(rx.Base):
    # TODO: Implement a system to check the platform,
    # config's uncaught changes as well
    host: HostEntryModelView
    platform: PlatformModelView

    web_bind_address: str = "http://127.0.0.1:8080"

    safe_host_entry: dict = {}
    uncaught: bool = False
    valid: bool = False    

    web_checked: bool = False
    advanced_expanded: bool = False
    agent_configuration_expanded: bool = False

    new_instance: bool = True

    def has_uncaught_changes(self) -> bool:
        return self.host.to_dict() != self.safe_host_entry

    def does_host_have_errors(self) -> bool:
        host_dict = self.host.to_dict()
        if not all([host_dict.get("id"), host_dict.get("ansible_user"), host_dict.get("ansible_host")]):
            logger.debug(f"Error: Missing host details {host_dict}")
        # If all fields are filled out, return false because no errors
        return (
            host_dict["id"] and \
            host_dict["ansible_user"] and \
            host_dict["ansible_host"] != ""
        )

# NOTE: when agents are added, some may have YAML configs, we need to prettify those by
# detecting type of string, and prettifying it.
# TODO: implement the functionality described above.

async def agents_off_catalog() -> List[AgentModelView]:
    catalog: Dict[str, AgentType] = await get_agent_catalog()
    agent_list: List[AgentModelView] = []

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

async def instances_from_api() -> dict[str, Instance]:
    platforms: list[PlatformDefinition] = await get_all_platforms()
    hosts: list[HostEntry] = await get_hosts()
    host_by_id: dict[str, HostEntry] = {}
    for h in hosts:
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

        # platform_status = await get_platform_status(
        #     get_request("http://localhost:8000/api/platforms/status", p.config.instance_name)
        #     )
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
                            config=prettify_json(agent.config)[0],
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
                    # logger.debug(f"Loaded usable CSV for config {config.path} inside agent {agent.identity}: {usable_csv}")
            # After going through the agent's config store and assigning the safe entries,
            # we can now assign the agent's safe_agent
            agent.safe_agent = agent.to_dict()

    return instances

class State(rx.State):
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
    def platform_deployed(self) -> bool:
        if self.current_uid == "":
            return False
        return False

    # === end of platform detail vars ===

    # ==== vars for connection validation ===

    @rx.var
    def connection_validity(self) -> bool:
        if self.current_uid == "":
            return True
        working_platform: Instance | None = self.platforms.get(self.current_uid, None)
        if working_platform is None:
            return False
        return self.connection_validity(working_platform)[0]
    
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
        return True
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
        
        self.list_of_agents = await agents_off_catalog()
        platforms_from_api = await instances_from_api()
        
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
        logger.debug(f"This is new instance_name: {self.platforms[new_uid].platform.config.instance_name}")

        yield NavigationState.route_to_platform(new_uid)

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
    def update_detail(self, field: str, value):
        working_platform_instance = self.platforms[self.current_uid]
        if field == "id":
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

        if working_platform.uncaught != False and working_platform.valid:
            working_platform.safe_host_entry = working_platform.host.to_dict()
            working_platform.uncaught = False

            depends = await get_ansible_service()
            deploy_platform(
                PlatformConfig(
                    instance_name=working_platform.platform.config.instance_name,
                    vip_address=working_platform.platform.config.vip_address
                ),
                ansible=depends
            )
            yield rx.toast.success("Deployed Successfully!")
     
    @rx.event
    async def handle_save(self):
        working_platform: Instance = self.platforms[self.current_uid]
        uid_copy = deepcopy(self.current_uid)

        logger.debug(f"this is the uid copy: {uid_copy}")
        all_platforms: list[PlatformDefinition] = await get_all_platforms()

        working_platform.safe_host_entry = working_platform.host.to_dict()
        working_platform.uncaught = False
        # logger.debug(f"getting the host id: {working_platform.safe_host_entry['id']}")
        
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
        # # Logging
        # logger.debug(f"Final base platform_request: {base_platform_request}")
        # logger.debug(f"this is my base platform_request: {base_platform_request}")
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
        request = CreateOrUpdateHostEntryRequest(**host_request)
        # logger.debug(f"this is the request: {request}")
        
        logger.debug(f"this is the uid copy: {uid_copy}")
        await add_host(request)
        inv_serv = await get_inventory_service()
        plat_serv = await get_platform_service()
        await create_platform(
            platform=base_platform_request,
            inventory_service=inv_serv,
            platform_service=plat_serv
            )
        
        # Lets say changes saved successfully and redirect to the new url while deleting our old one
        logger.debug(f"this is the uid copy: {uid_copy}")
        yield rx.toast.success("Changes saved successfully")
        self.platforms[working_platform.platform.config.instance_name] = working_platform
        logger.debug(f"this is the list of params: {list(self.platforms.keys())}")
        yield NavigationState.route_to_platform(working_platform.platform.config.instance_name)
        logger.debug(f"this is the uid about to deletee: {uid_copy}")
        yield State.delete_temp_uid(uid_copy)

    # NOTE: i would like to offload the uncaught and valid vars into the state vars because it's easier for the UI to read off of 
    # state vars, for faster development, ive kept these here and i'll change it once it's time to refine the code.
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
    
    # checking functions
    def check_instance_uncaught(self, working_platform: Instance) -> bool:
        uncaught: bool = False
        # check if host details are changed
        # logger.debug(f"I am checking host now..")
        if working_platform.host.to_dict() != working_platform.safe_host_entry:
            # logger.debug(f"Host is uncaught")
            uncaught = True

        # check if platform details are changed but skip the agents field as we will handle that separately
        if {k: v for k, v in working_platform.platform.to_dict().items() if k != 'agents'} != {k: v for k, v in working_platform.platform.safe_platform.items() if k != 'agents'}:
            # logger.debug(f"Platform is uncaught")
            uncaught = True

        # check if we added some new uncaught agents
        for agent in working_platform.platform.agents.values():
            if agent.is_new:
                logger.debug(f"we found an uncaught agent")
                uncaught = True
                # we can break out of this because we just needed to find at least one brand new uncaught agent
                # to render the platform as uncaught
                break

        # if working_platform.platform.to_dict() != working_platform.platform.safe_platform:
        #     # logger.debug(f"Platform is uncaught")
        #     uncaught = True
        
        return uncaught

    def check_instance_savable(self, working_platform: Instance) -> bool:
        savable = True

        # manually check the host... yuck.
        host_dict = working_platform.host.to_dict()
        if (
            host_dict["id"] == "" or \
            host_dict["ansible_user"] == "" or \
            host_dict["ansible_port"].isdigit() == False or \
            host_dict["ansible_host"] == ""
        ):
            logger.debug("Host is not valid...")
            logger.debug(f"here is the host to prove: {host_dict}")
            savable = False
        
        # check if platform details are valid 
        platform_valid, platform_valid_map = self.platform_validity(working_platform)
        if platform_valid == False:
            savable = False

        return savable

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
        # logger.debug(f"Checking if '{new_name}' exists in: {existing_names}")

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

@rx.page(route="/platform/[uid]", on_load=State.hydrate_state)
def platform_page() -> rx.Component:

    working_platform: Instance = State.platforms[State.current_uid]

    return rx.cond(State.is_hydrated, rx.fragment(app_layout(
        header(
            icon_button_wrapper.icon_button_wrapper(
                tool_tip_content="Go back to overview",
                icon_key="arrow-left",
                on_click=lambda: NavigationState.route_to_index()
            ),
            rx.text(f"""{
                    rx.cond(
                        working_platform.new_instance,
                        'New Platform',
                        f'Platform: {State.platform_title}'
                    )
                }""",
                trim="both",
                size="6"
            ),
        ),
        platform_tabs()
    )))

# TODO: clean up these components to make it more readable and separated. 
# These components all work if they have the right setup which follows:
# def function() -> rx.Component:
#   working_platform: Instance = State.platforms[State.current_uid]
#   return rx.cond(State.is_hydrated,
#             rest of component...
#             )


def platform_tabs() -> rx.Component:
    working_platform: Instance = State.platforms[State.current_uid]
    return rx.cond(
        State.is_hydrated,
        rx.box(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        "Status", value="status", disabled=rx.cond(
                            working_platform.platform.in_file,
                            False,
                            True
                        )
                    ),
                    rx.tabs.trigger("Configuration", value="configuration"),
                ),
                rx.tabs.content(
                    data_tab_content(),
                    value="status"
                ),
                rx.tabs.content(
                    rx.box(
                        configuration_tab_content(),
                        padding="1rem"
                    ),
                    value="configuration"
                ),
                default_value=rx.cond(
                    working_platform.platform.in_file,
                    "data",
                    "configuration"
                )
            )
        )
    )

# Config tab and it's components:
def configuration_tab_content() -> rx.Component:
    working_platform: Instance = State.platforms[State.current_uid]
    
    return rx.cond(State.is_hydrated, 
            rx.box(
                rx.accordion.root(
                    rx.accordion.item(
                        header="Connection",
                        value="connection",
                        # content=rx.box(
                        #     connection_accordion_content(working_platform)
                        # ),
                        content=rx.box(
                            rx.box(
                                form_entry.form_entry(
                                    "Host",
                                    rx.input(
                                        value= working_platform.host.id,
                                        on_change=lambda v: State.update_detail("id", v),
                                        size="3",
                                        required=True,
                                    ),
                                    required_entry=True,
                                ),
                                form_entry.form_entry(
                                    "Username",
                                    rx.input(
                                        value= working_platform.host.ansible_user,
                                        on_change=lambda v: State.update_detail("ansible_user", v),
                                        size="3",
                                        required=True,
                                    ),
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="Username must have SUDO permissions"
                                    ),
                                    required_entry=True,
                                ),
                                form_entry.form_entry(
                                    "Port SSH",
                                    rx.input(
                                        value= working_platform.host.ansible_port,
                                        on_change=lambda v: State.update_detail("ansible_port", v),
                                        size="3",
                                        required=True,
                                    ),
                                    required_entry=True,
                                    below_component=rx.cond(
                                        State.connection_ansible_port_validity == False,
                                        rx.text(
                                            "Port SSH must be a valid port number", 
                                            color_scheme="red"
                                        )
                                    ),
                                ),
                                rx.box(
                                    rx.hstack(
                                        rx.text("Toggle Advanced"),
                                        rx.cond(
                                            working_platform.advanced_expanded,
                                            rx.icon("chevron-up"),
                                            rx.icon("chevron-down")
                                        )
                                    ),
                                    class_name="toggle_advanced_button",
                                    on_click=lambda: State.toggle_advanced(State.current_uid)
                                ),
                                rx.cond(
                                    working_platform.advanced_expanded,
                                    rx.fragment(
                                        form_entry.form_entry(
                                            "HTTP Proxy",
                                            rx.input(
                                                value= working_platform.host.http_proxy,
                                                on_change=lambda v: State.update_detail("http_proxy", v),
                                                size="3",
                                                required=True,
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "HTTPS Proxy",
                                            rx.input(
                                                value= working_platform.host.https_proxy,
                                                on_change=lambda v: State.update_detail("https_proxy", v),
                                                size="3",
                                                required=True,
                                            )
                                        ),
                                        form_entry.form_entry(
                                            "VOLTTRON Home",
                                            rx.input(
                                                value= working_platform.host.volttron_home,
                                                on_change=lambda v: State.update_detail("volttron_home", v),
                                                size="3",
                                                required=True,
                                            )
                                        ),
                                    )
                                ),
                                class_name="platform_content_view"
                            ),
                            class_name="platform_content_container"
                        )
                    ),
                    rx.accordion.item(
                        header="Instance Configuration",
                        value="instance_configuration",
                        # content=rx.box(
                        #     instance_configuration_accordion_content(working_platform)
                        # ),
                        content=rx.box(
                            rx.box(
                                form_entry.form_entry( # validate
                                    "Instance Name",
                                    rx.vstack(
                                        rx.input(
                                            size="3",
                                            value=working_platform.platform.config.instance_name,
                                            on_change=lambda v: State.update_platform_config_detail("instance_name", v),
                                            required=True,
                                        ),
                                        align="center"
                                    ),
                                    below_component=rx.fragment(
                                        rx.cond(
                                            State.platform_instance_name_validity == False,
                                            rx.text(
                                                "Instance Name must contain only letters, numbers, hyphens, and underscores", 
                                                color_scheme="red"
                                            )
                                        ),
                                        rx.cond(
                                            State.platform_instance_name_not_in_use == False,
                                            rx.text(
                                                "Instance Name already in use", 
                                                color_scheme="red"
                                            )
                                        )
                                    ),
                                    required_entry=True,
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="Instance Name must contain only letters, numbers, hyphens, and underscores"
                                    )
                                ),
                                form_entry.form_entry( # validate
                                    "Vip Address",
                                    rx.vstack(
                                        rx.input(
                                            size="3",
                                            value=working_platform.platform.config.vip_address,
                                            on_change=lambda v: State.update_platform_config_detail("vip_address", v),
                                            required=True,
                                        ),  
                                        align="center"
                                    ),
                                    below_component=rx.cond(
                                        State.platform_vip_address_validity == False,
                                        rx.text(
                                            "Vip Address must be in the format tcp://<ip>:<port>", 
                                            color_scheme="red"
                                        )
                                    ),
                                    required_entry=True,
                                    upload=tile_icon(
                                        "badge-info",
                                        tooltip="Vip Address must be in the format tcp://<ip>:<port>"
                                    )
                                ),
                                form_entry.form_entry(
                                    "Web",
                                    rx.checkbox(
                                        size="3",
                                        checked=working_platform.web_checked,
                                        on_change=lambda: State.toggle_web()
                                    )
                                ),
                                rx.cond(
                                    working_platform.web_checked,
                                    rx.fragment(
                                        form_entry.form_entry(
                                            "Web Bind Address",
                                            rx.input(
                                                size="3",
                                                value=working_platform.web_bind_address,
                                                on_change=lambda v: State.update_platform_config_detail("web_bind_address", v),
                                                required=True,
                                            )
                                        )
                                    )
                                ),
                                rx.box(
                                    rx.hstack(
                                        rx.text("Agent Configuration"),
                                        rx.cond(
                                            working_platform.agent_configuration_expanded,
                                            rx.icon("chevron-up"),
                                            rx.icon("chevron-down")
                                        )
                                    ),
                                    class_name="toggle_advanced_button",
                                    on_click=lambda: State.toggle_agent_config_details()
                                ),
                                rx.box(
                                    rx.cond(
                                        working_platform.agent_configuration_expanded,
                                        rx.el.div(
                                            rx.box(
                                                rx.box(
                                                    rx.heading("Listed Agents", as_="h3"),
                                                    rx.foreach(
                                                        State.list_of_agents,
                                                        lambda agent, index: config_tile.config_tile(
                                                            agent.identity,
                                                            right_component=tile_icon(
                                                                "plus",
                                                                on_click=State.handle_adding_agent(agent)
                                                                ),
                                                            ),
                                                    ),
                                                    class_name="agent_config_view_content"
                                                ),
                                                class_name="agent_config_views"
                                            ),
                                            rx.box(
                                                rx.box(
                                                    rx.heading("Added Agents", as_="h3"),
                                                    rx.foreach(
                                                        working_platform.platform.agents,
                                                        lambda identity_agent_pair: config_tile.config_tile(
                                                            identity_agent_pair[1].identity,
                                                            left_component=tile_icon(
                                                                "trash-2",
                                                                on_click= lambda: State.handle_removing_agent(identity_agent_pair[0])
                                                                # on_click= lambda: State.handle_removing_agent(identity_agent_pair[0])
                                                            ),
                                                            right_component=tile_icon(
                                                                "settings",
                                                                on_click=lambda: NavigationState.route_to_agent_config(
                                                                    State.current_uid,
                                                                    identity_agent_pair[1].routing_id,
                                                                    identity_agent_pair[1]
                                                                )
                                                            ),
                                                            # This works but i dont want to implement it just yet, i want more info on how
                                                            # this should ideally work
                                                            # class_name=rx.cond(
                                                            #     State.new_agents_list.contains(identity_agent_pair[1].routing_id),
                                                            #     "agent_config_tile new",
                                                            #     "agent_config_tile"
                                                            # ),
                                                            # tooltip=rx.cond(
                                                            #     State.new_agents_list.contains(identity_agent_pair[1].routing_id),
                                                            #     "This agent is loaded with default configs",
                                                            #     ""
                                                            # )
                                                        )
                                                    ),
                                                    class_name="agent_config_view_content"
                                                ),
                                                class_name="agent_config_views"
                                            ),
                                            class_name="agent_config_container"
                                        ),
                                    )
                                ),
                                class_name="platform_content_view"
                            ),
                            class_name="platform_content_container"
                        )
                    ),
                    collapsible=True,
                    default_value=["connection"],
                    type="multiple",
                    variant="outline"
                ),
                rx.box(
                    rx.button(
                        "Save", 
                        size="4", 
                        variant="surface",
                        color_scheme="green",
                        on_click=lambda: State.handle_save(),
                        disabled=rx.cond(
                                (State.instance_savable)
                                & (State.instance_uncaught),
                                # (working_platform.uncaught),
                                False,
                                True
                            )
                        ),
                    rx.button(
                        rx.cond(
                            State.platform_deployed,
                            "Re-Deploy",
                            "Deploy"
                        ), 
                        size="4", 
                        variant="surface", 
                        color_scheme="blue",
                        on_click=lambda: State.handle_deploy(),
                        disabled=rx.cond(
                                (working_platform.uncaught == False)
                                & (working_platform.valid==True),
                                False,
                                True
                            )
                        ),
                    rx.button(
                            "Cancel", 
                            size="4", 
                            variant="surface", 
                            color_scheme="red",
                            on_click=lambda: State.handle_cancel(),
                            disabled=rx.cond(
                                State.instance_uncaught == False,
                                # working_platform.uncaught == False,
                                True,
                                False
                            )
                        ),
                    class_name="platform_view_button_row"
                    ),
            class_name="platform_view_container"
            )
        )

# Not in use as of right now
# def initialization_accordion(working_platform: Instance) -> rx.Component:
#     return rx.accordion.root(
#         rx.accordion.item(
#             header="Connection",
#             value="connection",
#             content=rx.box(
#                 connection_accordion_content(working_platform)
#             ),
#         ),
#         rx.accordion.item(
#             header="Instance Configuration",
#             value="instance_configuration",
#             content=rx.box(
#                 instance_configuration_accordion_content(working_platform)
#             ),
#         ),
#         collapsible=True,
#         default_value="connection",
#         type="multiple",
#         variant="outline"
#     )

# def instance_configuration_accordion_content(working_platform: Instance) -> rx.Component:
#     return rx.box(
#         rx.box(
#             form_entry.form_entry( # validate
#                 "Instance Name",
#                 rx.input(
#                     size="3",
#                     value=working_platform.platform.config.instance_name,
#                     on_change=lambda v: State.update_platform_config_detail("instance_name", v),
#                     required=True,
#                 ),
#                 required_entry=True,
#                 upload=tile_icon(
#                     "badge-info",
#                     tooltip="Instance Name must contain only letters, numbers, hyphens, and underscores"
#                 )
#             ),
#             form_entry.form_entry( # validate
#                 "Vip Address",
#                 rx.input(
#                     size="3",
#                     value=working_platform.platform.config.vip_address,
#                     on_change=lambda v: State.update_platform_config_detail("vip_address", v),
#                     required=True,
#                 ),
#                 required_entry=True,
#                 upload=tile_icon(
#                     "badge-info",
#                     tooltip="Vip Address must be in the format tcp://<ip>:<port>"
#                 )
#             ),
#             form_entry.form_entry(
#                 "Web",
#                 rx.checkbox(
#                     size="3",
#                     checked=working_platform.web_checked,
#                     on_change=lambda: State.toggle_web()
#                 )
#             ),
#             rx.cond(
#                 working_platform.web_checked,
#                 rx.fragment(
#                     form_entry.form_entry(
#                         "Web Bind Address",
#                         rx.input(
#                             size="3",
#                             value=working_platform.web_bind_address,
#                             on_change=lambda v: State.update_platform_config_detail("web_bind_address", v),
#                             required=True,
#                         )
#                     )
#                 )
#             ),
#             rx.box(
#                 rx.hstack(
#                     rx.text("Agent Configuration"),
#                     rx.cond(
#                         working_platform.agent_configuration_expanded,
#                         rx.icon("chevron-up"),
#                         rx.icon("chevron-down")
#                     )
#                 ),
#                 class_name="toggle_advanced_button",
#                 on_click=lambda: State.toggle_agent_config_details()
#             ),
#             rx.box(
#                 rx.cond(
#                     working_platform.agent_configuration_expanded,
#                     rx.el.div(
#                         rx.box(
#                             rx.box(
#                                 rx.heading("Listed Agents", as_="h3"),
#                                 rx.foreach(
#                                     State.list_of_agents,
#                                     lambda agent, index: agent_config_tile(
#                                         agent.identity, 
#                                         right_component=tile_icon(
#                                             "plus",
#                                             on_click=State.handle_adding_agent(agent)
#                                             ),
#                                         ),
#                                 ),
#                                 class_name="agent_config_view_content"
#                             ),
#                             class_name="agent_config_views"
#                         ),
#                         rx.box(
#                             rx.box(
#                                 rx.heading("Added Agents", as_="h3"),
#                                 rx.foreach(
#                                     working_platform.platform.agents,
#                                     lambda identity_agent_pair: agent_config_tile(
#                                         identity_agent_pair[0],
#                                         left_component=tile_icon(
#                                             "trash-2",
#                                             on_click= lambda: State.handle_removing_agent(identity_agent_pair[0])
#                                             # on_click= lambda: State.handle_removing_agent(identity_agent_pair[0])
#                                         ),
#                                         right_component=tile_icon(
#                                                 "settings",
#                                                 on_click=lambda: NavigationState.route_to_agent_config(
#                                                     State.current_uid,
#                                                     identity_agent_pair[1].routing_id,
#                                                     identity_agent_pair[1]
#                                                 )
#                                             )
#                                         )
#                                 ),
#                                 class_name="agent_config_view_content"
#                             ),
#                             class_name="agent_config_views"
#                         ),
#                         class_name="agent_config_container"
#                     ),
#                 )
#             ),
#             class_name="platform_content_view"
#         ),
#         class_name="platform_content_container"
#     )

# def connection_accordion_content(working_platform: Instance) -> rx.Component:
#     return rx.box(
#         rx.box(
#             form_entry.form_entry(
#                 "Host",
#                 rx.input(
#                     value= working_platform.host.id,
#                     on_change=lambda v: State.update_detail("id", v),
#                     size="3",
#                     required=True,
#                 ),
#                 required_entry=True,
#             ),
#             form_entry.form_entry(
#                 "Username",
#                 rx.input(
#                     value= working_platform.host.ansible_user,
#                     on_change=lambda v: State.update_detail("ansible_user", v),
#                     size="3",
#                     required=True,
#                 ),
#                 required_entry=True,
#             ),
#             form_entry.form_entry(
#                 "Port SSH",
#                 rx.input(
#                     value= working_platform.host.ansible_port,
#                     on_change=lambda v: State.update_detail("ansible_port", v),
#                     size="3",
#                     required=True,
#                     type="number"
#                 ),
#                 required_entry=True,
#             ),
#             rx.box(
#                 rx.hstack(
#                     rx.text("Toggle Advanced"),
#                     rx.cond(
#                         working_platform.advanced_expanded,
#                         rx.icon("chevron-up"),
#                         rx.icon("chevron-down")
#                     )
#                 ),
#                 class_name="toggle_advanced_button",
#                 on_click=lambda: State.toggle_advanced(State.current_uid)
#             ),
#             rx.cond(
#                 working_platform.advanced_expanded,
#                 rx.fragment(
#                     form_entry.form_entry(
#                         "HTTP Proxy",
#                         rx.input(
#                             value= working_platform.host.http_proxy,
#                             on_change=lambda v: State.update_detail("http_proxy", v),
#                             size="3",
#                             required=True,
#                         )
#                     ),
#                     form_entry.form_entry(
#                         "HTTPS Proxy",
#                         rx.input(
#                             value= working_platform.host.https_proxy,
#                             on_change=lambda v: State.update_detail("https_proxy", v),
#                             size="3",
#                             required=True,
#                         )
#                     ),
#                     form_entry.form_entry(
#                         "VOLTTRON Home",
#                         rx.input(
#                             value= working_platform.host.volttron_home,
#                             on_change=lambda v: State.update_detail("volttron_home", v),
#                             size="3",
#                             required=True,
#                         )
#                     ),
#                 )
#             ),
#             class_name="platform_content_view"
#         ),
#         class_name="platform_content_container"
#     )

# Data tab and it's components
def data_tab_content() -> rx.Component: 
    return rx.cond(State.is_hydrated, rx.container(
        rx.text("this is data... in all of it's glory")
    ))


# General components
def agent_config_tile(text, left_component: rx.Component = False, right_component: rx.Component = False)->rx.Component:
    return rx.hstack(
        rx.cond(
            left_component,
            rx.flex(
                left_component,
                align="center",
                justify="center",
            )
        ),
        rx.flex(
            rx.text(text),
            class_name=f"agent_config_tile",
        ),
        rx.cond(
            right_component,
            rx.flex(        
                right_component,
                align="center",
                justify="center"
            )
        ),  
        spacing="2",
        align="center",
    )

