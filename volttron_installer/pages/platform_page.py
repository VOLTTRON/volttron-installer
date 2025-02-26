import reflex as rx
from ..layouts.app_layout import app_layout
from ..components.buttons import icon_button_wrapper, upload_button
from ..components.header.header import header
from ..components.tabs.state import PlatformState
from ..components.buttons.tile_icon import tile_icon
from ..components.buttons.icon_upload import icon_upload
from ..navigation.state import NavigationState
from ..components.form_components import form_entry
from ..backend.models import HostEntry, PlatformDefinition, ConfigStoreEntry
from ..components.custom_fields.text_editor import text_editor

# storing stuff here just for now, will move to a better place later
import typing
import string, random, json
from pydantic import BaseModel
from ..backend.endpoints import get_platforms, create_platform, CreatePlatformRequest, CreateOrUpdateHostEntryRequest, add_host
import asyncio

parts = typing.Literal["connection", "instance_configuration"]

class AgentDefinition(BaseModel):
    identity: str
    agent_source: str
    agent_running: bool = True
    has_config_store: bool = False
    agent_config: dict[str, str] = {}
    agent_config_store: list[ConfigStoreEntry] = []


class Instance(rx.Base):
    # TODO: Implement a system to check the platform,
    # config's uncaught changes as well
    host: HostEntry
    platform: PlatformDefinition

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
            print("Error: Missing host details", host_dict)
        print("\n\nTHIS SI ME HRADCORE CHECKING IF ITS VALID OR NOT")
        print("id", host_dict["id"]=="")
        print("user", host_dict["ansible_user"]=="")
        print("host", host_dict["ansible_host"]=="")
        print("\n")
        # If all fields are filled out, return false because no errors
        return (
            host_dict["id"] and \
            host_dict["ansible_user"] and \
            host_dict["ansible_host"] != ""
        )


class State(rx.State):
    platforms: dict[str, Instance] = {}

# =========== Putting this here for now, ideally will be inside Instance class ==============
    list_of_agents: list[AgentDefinition] = [
        AgentDefinition(identity="Agent 1", agent_source=""),
        AgentDefinition(identity="Agent 2", agent_source=""),
        AgentDefinition(identity="Agent 3", agent_source="")
    ]

    added_agents: list[AgentDefinition] = []

    # list_of_agents: list[str] = [
    #     "Agent 1",
    #     "Agent 2",
    #     "Agent 3",
    # ]

    # added_agents: list[str] =[]
# ==================================================================================================
    @rx.var(cache=True)
    def current_uid(self) -> str:
        return self.router.page.params.get("uid", "")

    @rx.event
    def handle_adding_agent(self, agent: AgentDefinition):
        # if agent_name in self.list_of_agents:
        #     self.added_agents.append(agent_name)
        new_agent = agent.model_copy()
        self.added_agents.append(new_agent)
        
    @rx.event
    def handle_removing_agent(self, index: int):
        self.added_agents.pop(index)

    @rx.event
    def cancel_changes(self):
        working_platform: Instance = self.platforms[self.current_uid]
        
        # Revert back to our previous host entry
        working_platform.host = HostEntry(**working_platform.safe_host_entry)
        working_platform.uncaught = False
        working_platform.valid = working_platform.does_host_have_errors()

    @rx.event
    async def generate_new_platform(self):
        new_uid = self.generate_unique_uid()
        new_host = HostEntry(id="", ansible_user="", ansible_host="")
        new_platform = PlatformDefinition()
        self.platforms[new_uid] = Instance(
            host=new_host, 
            platform=new_platform,
            safe_host_entry=new_host.to_dict()
            )

        nav_state: NavigationState = await self.get_state(NavigationState)
        await nav_state.create_platform_route(new_uid)

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
        print(f"this is the uncaught: {working_platform_instance.uncaught}")
        print(f"this is the valid: {working_platform_instance.valid}")

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
        print(f"bruhhhs: uncaught:{working_platform.uncaught} , valid{working_platform.valid}")

        if working_platform.uncaught != False and working_platform.valid:
            working_platform.safe_host_entry = working_platform.host.to_dict()
            working_platform.uncaught = False

            yield rx.toast.success("Deployed Successfully!")

    @rx.event
    def handle_save(self):
        working_platform: Instance = self.platforms[self.current_uid]
        print(f"bruhhhs: {working_platform.uncaught} , {working_platform.valid}")

        # if working_platform.uncaught and working_platform.valid:
        # Should just save anyway, we wont be able to deploy as long as its
        # not valid
        working_platform.safe_host_entry = working_platform.host.to_dict()
        working_platform.uncaught = False

        # NOTE, theres a problem here
        # this thing worked ONE time and hasn't worked since,

        request = CreateOrUpdateHostEntryRequest(**working_platform.host.to_dict())
        add_host(request)
        # await create_platform(
        #     CreatePlatformRequest(
        #         # working_platform.platform
        #         )
        #     )
        yield rx.toast.success("Changes saved successfully")

    @rx.event
    def handle_cancel(self):
        working_platform: Instance = self.platforms[self.current_uid]
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
            rx.text(f"Platform: {PlatformState.current_uid}", size="6"),
        ),
        rx.box(
            rx.accordion.root(
                rx.accordion.item(
                    header="Connection",
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
                                    # form_entry.form_entry(
                                    #     "SSH config stuff",
                                    #     rx.input(
                                    #         size="3",
                                    #         required=True,
                                    #     )
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
                                                    lambda agent: agent_config_tile(
                                                        agent.identity, 
                                                        right_component=tile_icon(
                                                            "plus",
                                                            on_click=lambda: State.handle_adding_agent(agent)
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
                                                    State.added_agents,
                                                    lambda agent, index: agent_config_tile(
                                                        agent.identity, 
                                                        left_component=tile_icon(
                                                            "trash-2",
                                                            on_click= lambda: State.handle_removing_agent(index)
                                                            ),
                                                        right_component=rx.dialog.root(
                                                                rx.dialog.trigger(
                                                                    tile_icon(
                                                                        "settings"
                                                                    )
                                                                ),
                                                                rx.dialog.content(
                                                                    agent_config_modal(agent, index)
                                                                )
                                                            ),
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
                    on_click=lambda: State.handle_cancel()
                    ),
                class_name="platform_view_button_row"
                ),
        class_name="platform_view_container"
        ),
    )))

def agent_config_modal(agent: AgentDefinition, index) -> rx.Component:
    return rx.flex(
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
                            size="3"
                        )
                    ),
                    form_entry.form_entry(
                        "Agent Config",
                        text_editor(
                            placeholder="Type out JSON, YAML, or upload a file!"
                        ),
                        upload=icon_upload()
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
                            icon_upload(),
                            rx.text("broz"),
                            rx.text("broz"),
                            rx.text("broz"),
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
        min_height="80vh",
        direction="column",
        spacing="3",
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