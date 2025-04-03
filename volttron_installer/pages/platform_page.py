import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.buttons import icon_button_wrapper, upload_button
from ..components.header.header import header
from ..components.buttons.tile_icon import tile_icon
from ..components.buttons.icon_upload import icon_upload
from ..navigation.state import NavigationState
from ..components.form_components import form_entry
from ..backend.models import AgentType, HostEntry, PlatformConfig, PlatformDefinition, ConfigStoreEntry, AgentDefinition
from ..components.custom_fields.text_editor import text_editor
# storing stuff here just for now, will move to a better place later
from typing import List, Dict, Literal
from typing import List, Dict, Literal
import string, random, json, csv, yaml
from ..backend.endpoints import get_all_platforms, create_platform, \
    CreatePlatformRequest, CreateOrUpdateHostEntryRequest, add_host, \
    get_agent_catalog, get_hosts, update_platform, get_inventory_service, \
    get_platform_service
from ..functions.create_component_uid import generate_unique_uid
from ..functions.conversion_methods import csv_string_to_usable_dict
from ..functions.validate_content import check_json
from ..functions.prettify import prettify_json
from loguru import logger
from ..model_views import HostEntryModelView, PlatformModelView, AgentModelView, ConfigStoreEntryModelView, PlatformConfigModelView
from copy import deepcopy
import re

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
            logger.debug("Error: Missing host details", host_dict)
        logger.debug("\n\nTHIS SI ME HRADCORE CHECKING IF ITS VALID OR NOT")
        logger.debug("id", host_dict["id"]=="")
        logger.debug("user", host_dict["ansible_user"]=="")
        logger.debug("host", host_dict["ansible_host"]=="")
        logger.debug("\n")
        # If all fields are filled out, return false because no errors
        return (
            host_dict["id"] and \
            host_dict["ansible_user"] and \
            host_dict["ansible_host"] != ""
        )

async def agents_off_catalog() -> List[AgentModelView]:
    catalog: Dict[str, AgentType] = await get_agent_catalog()
    agent_list: List[AgentModelView] = []

    for identity, agent in catalog.items():
        agent_list.append(
            AgentModelView(
                identity=str(identity),
                source=agent.source,
                config_store=[
                    ConfigStoreEntryModelView(
                        path=path,
                        data_type=entry.data_type,
                        value=str(entry.value),
                        uncommitted=False,
                        safe_entry={
                            "path": path,
                            "data_type": entry.data_type,
                            "value": str(entry.value)
                        }
                    ) for path, entry in agent.default_config_store.items()
                ],
                config=str(agent.default_config),
            )
        )
    return agent_list

# TODO complete this 
async def instances_from_api() -> dict[str, Instance]:
    platforms: list[PlatformDefinition] = await get_all_platforms()
    hosts: list[HostEntry] = await get_hosts()
    host_by_id = {}
    for h in hosts:
        host_by_id[h.id] = h

    return {
        p.config.instance_name: Instance(
            host=HostEntryModelView(
                
            ),
            platform=PlatformModelView(
                config=PlatformConfigModelView(
                    instance_name=p.config.instance_name,
                    vip_address=p.config.vip_address,
                ),
                agents={
                    identity: AgentModelView(
                        identity=identity,
                        source=agent.source,
                        # config=agent.config
                        config_store=[
                            ConfigStoreEntryModelView()
                        ]
                    )
                    for identity, agent in p.agents.items()
                }
            )
        ) for p in platforms
    }


class State(rx.State):
    #TODO once we save a platform, we create a routing id off of it's instance name, and redirect to it haha lolz
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
    
    # Events
    @rx.event
    async def hydrate_state(self):
        self.list_of_agents = await agents_off_catalog()

    @rx.event
    def handle_adding_agent(self, agent: AgentModelView):
        working_platform = self.platforms[self.current_uid]
        # if agent_name in self.list_of_agents:
        #     self.added_agents.append(agent_name)
        new_agent: AgentModelView = agent.copy()
        if new_agent.identity in working_platform.platform.agents:
            new_agent.identity = f"{new_agent.identity}_{len(list(working_platform.platform.agents.values()))}"
        new_agent.routing_id = self.generate_unique_uid()

        logger.debug("im going to add new component ids for config store...")
        # go through the config store, create new component ids for each config entry
        for i in new_agent.config_store:
            i.component_id = self.generate_unique_uid()
            logger.debug(f"added component uid: {i.component_id}")

        # Set up the safe agent for validation
        new_agent.safe_agent={
                    "identity": new_agent.identity,
                    "source": new_agent.source,
                    "config": new_agent.config
                }
        
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
        a = []
        for config in new_agent.config_store:
            # im kind of sick of all of this copy and pasting of block of code:
            # TODO find a better and safer way of doing this 
            working_dict = config.csv_variants[config.selected_variant]
            config.csv_header_row = list(working_dict.keys()) 
            config.formatted_csv = [[working_dict[header] for header in config.csv_header_row] for i in range(10)]
            # ==============================================================
            config.safe_entry = config.dict()
            config.uncommitted = False
            a.append(config.safe_entry)
        logger.debug(f"safe entries all around: {a}")
        working_platform.platform.agents[new_agent.identity] = new_agent
        
    @rx.event
    def handle_removing_agent(self, identity: str):
        working_platform = self.platforms[self.current_uid]
        del(working_platform.platform.agents[identity])

    @rx.event
    def handle_cancel(self):
        working_platform: Instance = self.platforms[self.current_uid]
        
        # Revert back to our previous host entry
        working_platform.host = HostEntryModelView(**working_platform.safe_host_entry)
        working_platform.uncaught = False
        working_platform.valid = working_platform.does_host_have_errors()
        logger.debug("i pressed cancel,")
        yield rx.toast.info("Changes Reverted.")

    @rx.event
    async def generate_new_platform(self):
        new_uid = self.generate_unique_uid()
        new_host = HostEntryModelView(id="", ansible_user="", ansible_host="")
        new_platform = PlatformModelView(config=PlatformConfigModelView(), in_file=False)
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
        else:
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
    def handle_deploy(self):
        working_platform: Instance = self.platforms[self.current_uid]

        if working_platform.uncaught != False and working_platform.valid:
            working_platform.safe_host_entry = working_platform.host.to_dict()
            working_platform.uncaught = False

            yield rx.toast.success("Deployed Successfully!")

    @rx.event
    async def handle_save(self):
        working_platform: Instance = self.platforms[self.current_uid]
        all_platforms: list[PlatformDefinition] = await get_all_platforms()
        # if working_platform.uncaught and working_platform.valid:
        # Should just save anyway, we wont be able to deploy as long as its
        # not valid.
        # actually, this sort of complicates things, like what if we are saving the same
        # platform? does that change stuff

        # if workking_platform not in await endpoints.get_platforms()
        # then we one time do this, every other time we save we would go
        # into the api and save from there directly 

        working_platform.safe_host_entry = working_platform.host.to_dict()
        working_platform.uncaught = False
        logger.debug(f"getting the host id: {working_platform.safe_host_entry['id']}")


        for identity, agent in working_platform.platform.agents.items():
            if agent.identity != "":
                logger.debug(f"Debug: Checking {identity}")
                for config in agent.config_store:
                    if config.safe_entry["path"] != "":
                        logger.debug(f"Debug: Valid Config Path: {config.path}")
                        logger.debug(f"Data Type: {config.data_type}, Value: {config.value}")
                    else:
                        logger.debug(f"Debug: Ignored Config Path: {config.path}")

        platform_agents: dict[str, AgentDefinition] = {}
        for identity, agent in working_platform.platform.agents.items():
            if agent.safe_agent["identity"] != "":
                config_store: dict[str, ConfigStoreEntry] = {}
                for config in agent.config_store:
                    if config.safe_entry.get("path"):
                        notes: str = config.safe_entry["path"] 
                        logger.debug(f"Adding Config Path to store: {notes}")
                        valid_field_name_for_config_pattern = re.compile(r"^[a-zA-Z_-][a-zA-Z0-9_-]*$")
                        logger.debug(f"this is the deepcopy that im injecting into entry: {notes}")
                        logger.debug(f"Validating config path: {valid_field_name_for_config_pattern.match(notes)}")
                        entry = ConfigStoreEntry(
                            path=notes,
                            data_type=config.safe_entry["data_type"],
                            value=config.safe_entry["value"]
                            )
                        logger.debug(f"initial path: {entry.path}, {type(entry.path)}")
                        # for some reason these guys appear as tuples??? what...
                        # entry.path=f"{str(notes)}",
                        # ===
                        logger.debug(f"Created ConfigStoreEntry: {entry}")
                        config_store[notes] = entry
                    else:
                        logger.debug(f"Skipped Config: {config.safe_entry.get('path', 'No Path')}")
                        
                platform_agents[identity] = AgentDefinition(
                    identity=agent.safe_agent["identity"],
                    source=agent.safe_agent["source"],
                    #config=agent.safe_agent["config"]
                    config_store=config_store
                )

        # Finally, create the base platform request
        base_platform_request = CreatePlatformRequest(
            host_id=working_platform.safe_host_entry["id"],
            config=PlatformConfig(
                instance_name=working_platform.platform.config.instance_name,
                vip_address=working_platform.platform.config.vip_address
            ),
            agents=platform_agents
        )

        logger.debug(f"Final base platform_request: {base_platform_request}")
        # base_platform_request= CreatePlatformRequest(
        #             host_id=working_platform.safe_host_entry["id"],
        #             config=PlatformConfig(
        #                 instance_name=working_platform.platform.config.instance_name,
        #                 vip_address=working_platform.platform.config.vip_address
        #                 ),
        #             agents={
        #                 identity: AgentDefinition(
        #                     identity=agent.identity,
        #                     source=agent.source,
        #                     config_store={
        #                         entry.path: ConfigStoreEntry(
        #                             path=entry.path,
        #                             data_type=entry.data_type,
        #                             value=entry.value
        #                         )
        #                         # only include valid and non "" config paths 
        #                         for entry in (
        #                             ConfigStoreEntryModelView(
        #                                 # IF THE CONFIG PATH IS SOOOOO VALID, WHY ISNT IT SHOWING UP RIGHT HERE OMGGGGGG
        #                                 path=config.path,
        #                                 data_type=config.data_type,
        #                                 value=config.value
        #                             ) for config in agent.config_store if config.safe_entry["path"] != ""
        #                         )
        #                     }
        #                 )
        #                 # only include non "" agent identities
        #                 for identity, agent in working_platform.platform.agents.items() if agent.identity != ""
        #             }
        #         )

        logger.debug(f"this is my base platform_request: {base_platform_request}")
        if working_platform.platform.config.instance_name in [p.config.instance_name for p in all_platforms]:
            logger.debug("yes we have committed this already")
            update_platform(
                working_platform.platform.config.instance_name,
                base_platform_request
            )
            yield rx.toast.success("Changes saved successfully")
            return
                
        request = CreateOrUpdateHostEntryRequest(**working_platform.host.to_dict())
        logger.debug(f"this is the request: {request}")
        
        await add_host(request)
        inv_serv = await get_inventory_service()
        plat_serv = await get_platform_service()
        await create_platform(
            platform=base_platform_request,
            inventory_service=inv_serv,
            platform_service=plat_serv
            )
        working_platform.platform.in_file = True
        yield rx.toast.success("Changes saved successfully")

    # deprecated
    @rx.event
    def save_agent_config(self, identity_agent_pair: tuple[str, AgentModelView]):
        stable_identity: str = identity_agent_pair[0]
        agent: AgentModelView = identity_agent_pair[1]
        working_platform = self.platforms[self.current_uid]
        if stable_identity != agent.identity:
            if stable_identity not in working_platform.platform.agents:
                new_agents_dict: dict[str, AgentModelView] = {}
                for key, value in working_platform.platform.agents.items():
                    if key == stable_identity:
                        key = agent.identity
                    new_agents_dict[key] = value
                working_platform.platform.agents=new_agents_dict
            else:
                #TODO
                # Throw an error
                pass
        # working_platform.platform.agents[identity_agent_pair[0]]
        ...

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
            rx.cond(
                working_platform.new_instance,
                rx.text(f"New Platform", size="6"),
                rx.text(f"Platform: {working_platform.platform.config.instance_name}", size="6"),
            )
        ),
        platform_tabs()
    )))

# Components: dont work for whatever reason
def platform_tabs() -> rx.Component:
    working_platform: Instance = State.platforms[State.current_uid]
    return rx.cond(
        State.is_hydrated,
        rx.box(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        "Data", value="data", disabled=rx.cond(
                            working_platform.platform.in_file,
                            False,
                            True
                        )
                    ),
                    rx.tabs.trigger("Configuration", value="configuration"),
                ),
                rx.tabs.content(
                    rx.text("data"),
                    value="data"
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
                                        type="number"
                                    ),
                                    required_entry=True,
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
                                    rx.input(
                                        size="3",
                                        value=working_platform.platform.config.instance_name,
                                        on_change=lambda v: State.update_platform_config_detail("instance_name", v),
                                        required=True,
                                    )
                                ),
                                form_entry.form_entry( # validate
                                    "Vip Address",
                                    rx.input(
                                        size="3",
                                        value=working_platform.platform.config.vip_address,
                                        on_change=lambda v: State.update_platform_config_detail("vip_address", v),
                                        required=True,
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
                                                        lambda agent, index: agent_config_tile(
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
                                                        lambda identity_agent_pair: agent_config_tile(
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
                                                                )
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
                    default_value="connection",
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
                                working_platform.uncaught,
                                False,
                                True
                            )
                        ),
                    rx.button(
                        "Deploy", 
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
                                working_platform.uncaught == False,
                                True,
                                False
                            )
                        ),
                    class_name="platform_view_button_row"
                    ),
            class_name="platform_view_container"
            )
        )

def initialization_accordion(working_platform: Instance) -> rx.Component:
    return rx.accordion.root(
        rx.accordion.item(
            header="Connection",
            value="connection",
            content=rx.box(
                connection_accordion_content(working_platform)
            ),
        ),
        rx.accordion.item(
            header="Instance Configuration",
            value="instance_configuration",
            content=rx.box(
                instance_configuration_accordion_content(working_platform)
            ),
        ),
        collapsible=True,
        default_value="connection",
        type="multiple",
        variant="outline"
    )

def instance_configuration_accordion_content(working_platform: Instance) -> rx.Component:
    return rx.box(
        rx.box(
            form_entry.form_entry( # validate
                "Instance Name",
                rx.input(
                    size="3",
                    value=working_platform.platform.config.instance_name,
                    on_change=lambda v: State.update_platform_config_detail("instance_name", v),
                    required=True,
                )
            ),
            form_entry.form_entry( # validate
                "Vip Address",
                rx.input(
                    size="3",
                    value=working_platform.platform.config.vip_address,
                    on_change=lambda v: State.update_platform_config_detail("vip_address", v),
                    required=True,
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
                                    lambda agent, index: agent_config_tile(
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
                                    lambda identity_agent_pair: agent_config_tile(
                                        identity_agent_pair[0],
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
                                            )
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

def connection_accordion_content(working_platform: Instance) -> rx.Component:
    return rx.box(
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
                required_entry=True,
            ),
            form_entry.form_entry(
                "Port SSH",
                rx.input(
                    value= working_platform.host.ansible_port,
                    on_change=lambda v: State.update_detail("ansible_port", v),
                    size="3",
                    required=True,
                    type="number"
                ),
                required_entry=True,
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



