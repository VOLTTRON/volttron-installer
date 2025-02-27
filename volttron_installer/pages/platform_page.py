import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.buttons import icon_button_wrapper, upload_button
from ..components.header.header import header
from ..components.buttons.tile_icon import tile_icon
from ..components.buttons.icon_upload import icon_upload
from ..navigation.state import NavigationState
from ..components.form_components import form_entry
from ..backend.models import AgentType, HostEntry, PlatformDefinition, ConfigStoreEntry
from ..components.custom_fields.text_editor import text_editor
# storing stuff here just for now, will move to a better place later
from typing import List, Dict, Literal
from typing import List, Dict, Literal
import string, random, json, csv, yaml
from pydantic import BaseModel, root_validator, model_validator
from ..backend.endpoints import get_all_platforms, create_platform, \
    CreatePlatformRequest, CreateOrUpdateHostEntryRequest, add_host, \
    get_agent_catalog
from ..functions.create_component_uid import generate_unique_uid
from loguru import logger
from copy import deepcopy
from ..model_views import HostEntryModelView, PlatformModelView, AgentModelView, ConfigStoreEntryModelView


parts = Literal["connection", "instance_configuration"]

class AgentDefinition(BaseModel):
    identity: str
    agent_source: str = ""
    agent_running: bool = True
    has_config_store: bool = False
    agent_config: dict[str, str] = {}
    agent_config_store: list[ConfigStoreEntry] = []

    # instead of agent_config, we work with config because we
    # need it to be a string. This is expected to be a JSON
    # serealizable string
    config: str = ""

    # @model_validator()
    # def allow_empty_agent_source(cls, values):
    #     if 'agent_source' not in values or values['agent_source'] is None:
    #         values['agent_source'] = ''
    #     return values



 
class Instance(rx.Base):
    # TODO: Implement a system to check the platform,
    # config's uncaught changes as well
    host: HostEntryModelView
    platform: PlatformModelView

    web_bind_address: str = ""

    safe_host_entry: dict = {}
    uncaught: bool = False
    valid: bool = False    

    web_checked: bool = False
    advanced_expanded: bool = False
    agent_configuration_expanded: bool = False

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

async def agents_off_catalog() -> List[AgentDefinition]:
    catalog: Dict[str, AgentType] = await get_agent_catalog()
    agent_list: List[AgentModelView] = []

    for identity, agent in catalog.items():
        agent_list.append(
            AgentDefinition(
                identity=str(identity),
                source=agent.source,
                config_store=[
                    ConfigStoreEntryModelView(
                        path=path,
                        data_type=entry.data_type,
                        value=str(entry.value),
                    ) for path, entry in agent.default_config_store.items()
                ],
                config=str(agent.default_config),
            )
        )
    return agent_list


class State(rx.State):
    platforms: dict[str, Instance] = {}
    list_of_agents: list[AgentModelView] = []

# =========== Putting this here for now, ideally will be inside Instance class ==============
        # initialize with agent_catalogue
        
        # AgentDefinition(identity="Agent 1", agent_source=""),
        # AgentDefinition(identity="Agent 2", agent_source=""),
        # AgentDefinition(identity="Agent 3", agent_source="")
    

    thingy: list[str] = ["bro", "no", "sense"]
# ==================================================================================================
    # Vars
    # @rx.var(cache=True)
    # def current_agent(self) -> AgentModelView:
    #     current_platform = self.platforms[self.current_uid]

    #     return current_platform.platform.agents[self.working_agent_identity] if self.working_agent_identity in current_platform.platform.agents else AgentModelView()

    @rx.var(cache=True)
    def current_uid(self) -> str:
        return self.router.page.params.get("uid", "")

    # Events
    @rx.event
    async def hydrate_state(self):
        self.list_of_agents = await agents_off_catalog()

    @rx.event
    async def hydrate_state(self):
        self.list_of_agents = await agents_off_catalog()

    @rx.event
    def set_working_agent(self, agent: AgentModelView, identity: str = ""):
        self.working_agent = agent
        self.working_agent_identity = identity
        self.working_agent_config_store = agent.config_store
        logger.debug(f"working with {self.working_agent.identity}")

    @rx.event
    def clear_working_agent(self):
        self.working_agent = ""
        self.working_agent_config_store = []

    @rx.event
    def handle_adding_agent(self, agent: AgentDefinition):
        working_platform = self.platforms[self.current_uid]
        # if agent_name in self.list_of_agents:
        #     self.added_agents.append(agent_name)
        new_agent = agent.model_copy()
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
        working_platform.platform.agents[new_agent.identity] = new_agent
        # self.added_agents.append(new_agent)
        
    @rx.event
    def handle_removing_agent(self, identity: str):
        working_platform = self.platforms[self.current_uid]
        del(working_platform.platform.agents[identity])
    def handle_removing_agent(self, identity: str):
        working_platform = self.platforms[self.current_uid]
        del(working_platform.platform.agents[identity])

    @rx.event
    def update_agent_detail(self, agent: AgentModelView, field: str, value: str, id: str):
        setattr(agent, field, value)
        logger.debug(f"Lookie: \n{json.dumps(agent.dict(), indent=4)}")
        yield rx.set_value(id, value)

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
        new_platform = PlatformModelView()
        self.platforms[new_uid] = Instance(
                host=new_host, 
                platform=new_platform,
                safe_host_entry=new_host.to_dict()
            )

        # nav_state: NavigationState = await self.get_state(NavigationState)
        # await nav_state.create_platform_route(new_uid)

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

        # if working_platform.uncaught and working_platform.valid:
        # Should just save anyway, we wont be able to deploy as long as its
        # not valid
        working_platform.safe_host_entry = working_platform.host.to_dict()
        working_platform.uncaught = False

        # NOTE, theres a problem here
        # this thing worked ONE time and hasn't worked since,

        request = CreateOrUpdateHostEntryRequest(**working_platform.host.to_dict())
        await add_host(request)
        await create_platform(
            CreatePlatformRequest(
                    config=PlatformConfig(**working_platform.platform.config.to_dict()),
                    agents={
                        identity: AgentDefinition(
                            identity=agent.identity,
                            source=agent.source,
                            config_store={
                                entry.path: ConfigStoreEntry(
                                    path=entry.path,
                                    data_type=entry.data_type,
                                    value=entry.value
                                )
                                for entry in agent.config_store
                            }
                        )
                        for identity, agent in working_platform.platform.agents.items()
                    }
                )
            )
        yield rx.toast.success("Changes saved successfully")

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
                # Through an error
                pass
        # working_platform.platform.agents[identity_agent_pair[0]]
        ...

    @rx.event
    async def handle_config_store_entry_upload(self, files: list[rx.UploadFile]):
        print(f"Starting config store entry upload process for: {self.working_agent.identity}...")
        
        # Saving the actual file
        file = files[0]
        print(f"Received file: {file.filename}")
        
        upload_data = await file.read()
        print("File data read successfully.")
        
        outfile= (
            rx.get_upload_dir() / file.filename
        )
        print(f"Saving file to: {outfile}")
        
        with outfile.open("wb") as file_object:
            file_object.write(upload_data)
        print("File saved successfully.")

        result: str =""
        file_type: str = ""

        # Open and print the contents of the file to the console
        if file.filename.endswith('.json'):
            print("Detected JSON file format.")
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                print("JSON content read successfully.")
                print("Printing JSON content:")
                print(json.dumps(data, indent=4))
                file_type="JSON"
                result = json.dumps(data, indent=4)

        elif file.filename.endswith('.csv'):
            print("Detected CSV file format.")
            with open(outfile, 'r') as file_object:
                reader = csv.reader(file_object)
                print("CSV content read successfully.")
                print("Printing CSV content row by row:")
                for row in reader:
                    print(row)
                file_type="CSV"
        else:
            print("Unsupported file format")
            yield rx.toast.error("Unsupported file format")
            return
        
        # Adding config store entry
        self.working_agent.agent_config_store.append(
            ConfigStoreEntry(
                path="",
                data_type=file_type,
                value=result
            )
        )
    
    @rx.event
    async def handle_agent_config_upload(self, files: list[rx.UploadFile]):

        print(f"Starting file upload process for: {self.working_agent.identity}...")
        
        # Saving the actual file
        file = files[0]
        logger.debug(f"Received file: {file.filename}")
        
        upload_data = await file.read()
        logger.debug("File data read successfully.")
        
        outfile= (
            rx.get_upload_dir() / file.filename
        )
        logger.debug(f"Saving file to: {outfile}")
        
        with outfile.open("wb") as file_object:
            file_object.write(upload_data)
        logger.debug("File saved successfully.")

        result: str =""
        file_type: str = ""

        # Open and logger.debug the contents of the file to the console
        if file.filename.endswith('.json'):
            logger.debug("Detected JSON file format.")
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                logger.debug("JSON content read successfully.")
                logger.debug("printing JSON content:")
                logger.debug(json.dumps(data, indent=4))
                file_type="JSON"
                result = json.dumps(data, indent=4)

        elif file.filename.endswith('.csv'):
            logger.debug("Detected CSV file format.")
            with open(outfile, 'r') as file_object:
                reader = csv.reader(file_object)
                logger.debug("CSV content read successfully.")
                logger.debug("printing CSV content row by row:")
                for row in reader:
                    logger.debug(row)
                file_type="CSV"
        else:
            logger.debug("Unsupported file format")
            yield rx.toast.error("Unsupported file format")
            return
        
        # Adding config store entry
        self.working_agent.config_store.append(
            ConfigStoreEntryModelView(
                path="",
                data_type=file_type,
                value=result
            )
        )
        logger.debug(f"this is my agent: {json.dumps(self.working_agent.dict(), indent=4)}")
    
    @rx.event
    async def handle_agent_config_upload(self, files: list[rx.UploadFile]):

        logger.debug(f"Starting file upload process for: {self.working_agent.identity}...")
        
        file = files[0]
        logger.debug(f"Received file: {file.filename}")
        
        upload_data = await file.read()
        logger.debug("File data read successfully.")
        
        outfile= (
            rx.get_upload_dir() / file.filename
        )
        logger.debug(f"Saving file to: {outfile}")
        
        with outfile.open("wb") as file_object:
            file_object.write(upload_data)
        logger.debug("File saved successfully.")

        result: str =""

        # logger.debug the contents of the file to the console
        if file.filename.endswith('.json'):
            logger.debug("Detected JSON file format.")
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                logger.debug("JSON content read successfully.")
                logger.debug("printing JSON content:")
                logger.debug(json.dumps(data, indent=4))
                result = json.dumps(data, indent=4)

        elif file.filename.endswith('.yaml') or file.filename.endswith('.yml'):
            logger.debug("Detected YAML file format.")
            with open(outfile, 'r') as file_object:
                data = yaml.safe_load(file_object)
                logger.debug("YAML content read successfully.")
                logger.debug("printing YAML content:")
                logger.debug(yaml.dump(data, sort_keys=False, default_flow_style=False))
                result = yaml.dump(data, sort_keys=False, default_flow_style=False)
        else:
            logger.debug("Unsupported file format")

        # self.working_agent.config = result
        # print(self.working_agent.config)
        print("File processing completed.")
        # yield self.update_agent_detail(self.working_agent, "config", result, "agent_config_field")
        setattr(self.working_agent, "config", result)
        yield rx.set_value(id, result)

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

@rx.page(route="/platform/[uid]")
def platform_page() -> rx.Component:

    working_platform: Instance = State.platforms[State.current_uid]

    return rx.cond(State.is_hydrated, rx.fragment(app_layout(
        header(
            icon_button_wrapper.icon_button_wrapper(
                tool_tip_content="Go back to overview",
                icon_key="arrow-left",
                on_click=lambda: NavigationState.route_to_index()
            ),
            rx.text(f"Platform: {State.current_uid}", size="6"),
        ),
        rx.box(
            rx.accordion.root(
                rx.accordion.item(
                    header="Connection",
                    value="connection",
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
                                    # ok wow so things can render just fine here but when we put it in the modal everything breaks...
                                    # got it...
                                    # rx.foreach(
                                    #     State.thingy,
                                    #     lambda item: agent_config_tile(text="am i real")
                                    # ),
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
                    content=rx.box(
                        rx.box(
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
                ),
                collapsible=True,
                default_value="connection",
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
        ),
    )))

def agent_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            tile_icon("settings")
        ),
        rx.dialog.content(
            rx.dialog.title("Agent Details"),
            rx.dialog.description(
                f"Configuration for "
            ),
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Settings", value="1")
                ),
                rx.tabs.content(
                    rx.vstack(
                        # Agent specific content here
                        rx.text(f"Agent ID:"),
                        rx.foreach(
                            State.thingy,
                            lambda thing: rx.text(text=thing)
                        )
                        # Other agent details...
                    ),
                    value="1"
                ),
                default_value="1"
            )
        )
    )

def agent_config_modal(identity_agent_pair: tuple[str, AgentModelView]) -> rx.Component:
    working_platform: Instance = State.platforms[State.current_uid]
    stable_identity = identity_agent_pair[0]
    agent: AgentModelView = identity_agent_pair[1]
    return rx.cond(State.working_agent !="", rx.cond(State.is_hydrated, rx.fragment(rx.flex(
        rx.heading(stable_identity, as_="h3"),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Agent Config", value="1"),
                rx.tabs.trigger("Config Store Entries", value="2")
            ),
            rx.tabs.content(
                rx.flex(
                    form_entry.form_entry(
                        "Identity",
                        rx.input(
                            value=working_platform.platform.agents[stable_identity].identity,
                            on_change=lambda v: State.update_agent_detail(
                                working_platform.platform.agents[stable_identity], 
                                "identity", 
                                v, 
                                "agent_identity_field"
                            ),
                            size="3",
                            id="agent_identity_field"
                        )
                    ),
                    form_entry.form_entry(
                        "Source",
                        rx.input(
                            size="3",
                            # testing
                            value=agent.source,
                            on_change=lambda v: State.update_agent_detail(agent, "source", v, "agent_source_field"),
                            id="agent_source_field"
                        )
                    ),                    
                    form_entry.form_entry(
                        "Agent Config",
                        text_editor(
                            placeholder="Type out JSON, YAML, or upload a file!",
                            # value=working_platform.platform.agents[stable_identity].config,
                            value=State.working_agent.config,
                            on_change=lambda v: State.update_agent_detail(
                                State.working_agent, 
                                "config", 
                                v, 
                                "agent_config_field"
                                ),
                            id="agent_config_field"
                        ),
                        upload=rx.upload.root(
                            icon_upload(),
                            id="agent_config_upload",
                            max_files=1,
                            accept={
                                "text/yaml" : [".yml", ".yaml"],
                                "text/json" : [".json"]
                            },
                            on_drop=State.handle_agent_config_upload(
                                # agent, 
                                rx.upload_files(upload_id="agent_config_upload")
                            )
                        )
                    ),
                    padding_top="1rem",
                    direction="column",
                    class_name="agent_config_modal",
                    spacing="3",
                ),
                value="1"
            ),
            rx.tabs.content(
                # This will look like the 
                rx.flex(
                    rx.flex(
                        rx.flex(
                            rx.upload.root(
                                icon_upload(),
                                id="config_store_entry_upload",
                                accept={
                                    "text/csv" : [".csv"],
                                    "text/json" : [".json"]
                                },
                                on_drop=State.handle_config_store_entry_upload(
                                    rx.upload_files(upload_id="config_store_entry_upload")
                                )
                            ),

                            # rx.cond(
                            #     State.working_agent != "",
                            #     rx.cond(
                            #         State.working_agent.config_store.length() > 0,
                            #         rx.foreach(
                            #             State.working_agent.config_store,
                            #             lambda item: agent_config_tile(f"heyy")  # Add item parameter
                            #         ),
                            #         rx.text("No items")  # Add else case
                            #     ),
                            #     rx.text("No agent selected")  # Add else case
                            # ),
                            direction="column",
                            flex="1",
                            align="center",
                            spacing="4"
                        ),
                        border="1px solid white",
                        border_radius=".5rem",
                        padding="1rem",
                        flex="1"
                    ),
                    rx.flex(
                        rx.flex(
                            # rx.cond(
                            #     True,
                                rx.box(),
                            # )
                            direction="column",
                            flex="1",
                            align="center"
                        ),
                        # border="1px solid white",
                        border_radius=".5rem",
                        padding="1rem",
                        flex="1"
                    ),
                    align="center",
                    spacing="4",
                    direction="row",
                    padding_top="1rem",
                    width="100%"
                ),
                value="2"
            ),
            default_value="1"
        ),
        rx.hstack(
            rx.button(
                "Save",
                variant="surface",
                color_scheme="green",
                #on_click
            ), 
            align_items="end",
            justify="end"
        ),
        min_height="clamp(90vh, 30rem)",
        direction="column",
        spacing="3",
    )
)))

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



