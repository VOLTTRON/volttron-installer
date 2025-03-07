import reflex as rx
from ..layouts.app_layout import app_layout
from ..model_views import AgentModelView, ConfigStoreEntryModelView
from ..components.header.header import header
from ..components.buttons import icon_button_wrapper, icon_upload, tile_icon
from ..components.form_components import *
from ..components.custom_fields import text_editor, csv_field
from ..components.tiles.config_tile import config_tile
from ..functions.create_component_uid import generate_unique_uid

from .platform_page import State as AppState
from .platform_page import Instance
from ..navigation.state import NavigationState

import json, csv, yaml
from loguru import logger

class AgentConfigState(rx.State):
    # Store reference to working agent
    working_agent: AgentModelView = AgentModelView()
    selected_component_id: str = ""

    # this being named agent details doesn't make sense but whatever
    @rx.var
    def agent_details(self) -> dict:
        args = self.router.page.params
        uid = args.get("uid", "")
        agent_uid = args.get("agent_uid", "")
        return {"uid": uid, "agent_uid": agent_uid}

    @rx.event
    async def hydrate_working_agent(self):
        """Initialize working agent from platform state"""
        platform_state: AppState = await self.get_state(AppState)
        working_platform: Instance = platform_state.platforms[self.agent_details["uid"]]
        
        # Find agent by routing_id
        for agent in working_platform.platform.agents.values():
            if agent.routing_id == self.agent_details["agent_uid"]:
                self.working_agent = agent
                break

    @rx.event
    def update_agent_detail(self, field: str, value: str, id: str = None):
        """Update agent details directly"""
        setattr(self.working_agent, field, value)
        
        if id is not None:
            yield rx.set_value(id, value)

    @rx.event
    def update_config_detail(self, field: str, value: str, id: str = None):
        """Update a config store entry directly"""
        for config in self.working_agent.config_store:
            # get the working config
            if config.component_id == self.selected_component_id:
                logger.debug("updating details...")
                setattr(config, field, value)

                if id is not None:
                    yield rx.set_value(id, value)


    @rx.event
    async def handle_config_store_entry_upload(self, files: list[rx.UploadFile]):
        current_file = files[0]
        upload_data = await current_file.read()
        outfile = (rx.get_upload_dir() / current_file.filename)
        
        with outfile.open("wb") as file_object:
            file_object.write(upload_data)

        result: str = ""
        file_type: str = ""

        if current_file.filename.endswith('.json'):
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                file_type = "JSON"
                result = json.dumps(data, indent=4)
        elif current_file.filename.endswith('.csv'):
            with open(outfile, 'r') as file_object:
                reader = csv.reader(file_object)
                file_type = "CSV"
                # Handle CSV processing
        else:
            yield rx.toast.error("Unsupported file format")
            return
        
        agent = self.working_agent
        new_config_entry= ConfigStoreEntryModelView(
                path="",
                data_type=file_type,
                value=result,
                component_id=generate_unique_uid()
            )
        logger.debug(f"pls add: {new_config_entry.component_id}")
        agent.config_store.append(
            new_config_entry
        )
        logger.debug("agent config store entry was uploaded")

    @rx.event
    async def handle_agent_config_upload(self, files: list[rx.UploadFile]):
        file = files[0]
        upload_data = await file.read()
        outfile = (rx.get_upload_dir() / file.filename)
        
        with outfile.open("wb") as file_object:
            file_object.write(upload_data)

        result: str = ""

        if file.filename.endswith('.json'):
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                result = json.dumps(data, indent=4)
        elif file.filename.endswith('.yaml') or file.filename.endswith('.yml'):
            with open(outfile, 'r') as file_object:
                data = yaml.safe_load(file_object)
                result = yaml.dump(data, sort_keys=False, default_flow_style=False)
        else:
            yield rx.toast.error("Unsupported file format")
            return

        agent = self.working_agent
        agent.config = result
        yield rx.set_value("agent_config_field", result)

    @rx.event
    async def save_agent_config(self):
        """Save agent configuration"""
        agent = self.working_agent
        agent.uncaught = False
        agent.safe_agent = agent.dict()
        yield rx.toast.success("Agent configuration saved")

    @rx.event
    def print_config_properties(self, config: ConfigStoreEntryModelView):
        unpacked = config.dict()
        logger.debug(f"here is my config: \n {unpacked}")
        logger.debug("this is a component id ")
        logger.debug(config.component_id)

    @rx.event
    def set_component_id(self, component_id: str):
        if self.selected_component_id == component_id:
            self.selected_component_id = ""
        else:
            self.selected_component_id = component_id
        logger.debug("our new config entry")

@rx.page(route="/platform/[uid]/agent/[agent_uid]", on_load=AgentConfigState.hydrate_working_agent)
def agent_config_page() -> rx.Component:
    return app_layout(
        header(
            icon_button_wrapper.icon_button_wrapper(
                tool_tip_content="Go back to platform",
                icon_key="arrow-left",
                on_click=lambda: NavigationState.route_back_to_platform(
                    AgentConfigState.agent_details["uid"]
                )
            ),
            rx.heading(AgentConfigState.working_agent.safe_agent["identity"], as_="h3"),
        ),
        rx.flex(
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
                                value=AgentConfigState.working_agent.identity,
                                on_change=lambda v: AgentConfigState.update_agent_detail("identity", v),
                                size="3",
                            )
                        ),
                        form_entry.form_entry(
                            "Source", 
                            rx.input(
                                value=AgentConfigState.working_agent.source,
                                on_change=lambda v: AgentConfigState.update_agent_detail("source", v),
                                size="3",
                            )
                        ),
                        form_entry.form_entry(
                            "Agent Config",
                            text_editor.text_editor(
                                placeholder="Type out JSON, YAML, or upload a file!",
                                value=AgentConfigState.working_agent.config,
                                on_change=lambda v: AgentConfigState.update_agent_detail("config", v),
                            ),
                            upload=rx.upload.root( 
                                icon_upload.icon_upload(),
                                id="agent_config_upload",
                                max_files=1,
                                accept={
                                    "text/yaml" : [".yml", ".yaml"],
                                    "text/json" : [".json"]
                                },
                                on_drop=AgentConfigState.handle_agent_config_upload(
                                    # agent, 
                                    rx.upload_files(upload_id="agent_config_upload")
                                )
                            )
                        ),
                        direction="column",
                        justify="start",
                        spacing="6",
                        align="start",
                        padding="1rem"
                    ),
                    value="1"
                ),
                rx.tabs.content(
                    rx.flex(
                        rx.flex(
                            rx.flex(
                                rx.box(
                                    rx.upload.root(
                                        icon_upload.icon_upload(),
                                        id="config_store_entry_upload",
                                        accept={
                                            "text/csv": [".csv"],
                                            "text/json": [".json"]
                                        },
                                        on_drop=AgentConfigState.handle_config_store_entry_upload(
                                            rx.upload_files(upload_id="config_store_entry_upload")
                                        )
                                    ),
                                ),
                                rx.foreach(
                                    AgentConfigState.working_agent.config_store,
                                    lambda config: config_tile(
                                            text=config.path,
                                            right_component=tile_icon.tile_icon(
                                                "settings",
                                                class_name=rx.cond(
                                                    AgentConfigState.selected_component_id == config.component_id,
                                                    "icon_button active",  # Combined class names
                                                    "icon_button"
                                                ),
                                                # on_click=AgentConfigState.print_config_properties(config)
                                                on_click=lambda: AgentConfigState.set_component_id(config.component_id)
                                            )
                                        )
                                ),
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
                                rx.cond(
                                    AgentConfigState.selected_component_id != "",
                                    rx.fragment(
                                        rx.foreach(
                                            AgentConfigState.working_agent.config_store,
                                            lambda config: rx.cond(
                                                config.component_id == AgentConfigState.selected_component_id,
                                                rx.fragment(
                                                    form_entry.form_entry(
                                                        "Path",
                                                        rx.input(
                                                            size="3",
                                                            value=config.path,
                                                            on_change=lambda v: AgentConfigState.update_config_detail("path", v)
                                                        )
                                                    ),
                                                    form_entry.form_entry(
                                                        "Data Type",
                                                        rx.radio(
                                                            ["JSON", "CSV"],
                                                            value=config.data_type,
                                                            on_change=lambda v: AgentConfigState.update_config_detail("data_type", v)
                                                        )
                                                    ),
                                                    form_entry.form_entry(
                                                        "Config",
                                                        rx.cond(
                                                            config.data_type=="JSON",
                                                            text_editor.text_editor(
                                                                value=config.value
                                                            ),
                                                            csv_field.csv_data_field(config)
                                                        ),
                                                        upload=rx.upload.root( 
                                                            icon_upload.icon_upload(),
                                                            id="config_upload",
                                                            max_files=1,
                                                            accept={
                                                                "text/csv" : [".csv"],
                                                                "text/json" : [".json"]
                                                            },
                                                            # on_drop=AgentConfigState.handle_config_entry_config_upload(
                                                            #     # agent, 
                                                            #     rx.upload_files(upload_id="config_upload")
                                                            # )
                                                        )
                                                    ),
                                                )
                                            )
                                        )
                                    ),
                                    rx.box(rx.text("baka"))
                                ),
                                direction="column",
                                flex="1",
                                align="start",
                                spacing="6",
                            ),
                            # border="1px solid white",
                            border_radius=".5rem",
                            padding="1rem",
                            flex="1"
                        ),
                        align="start",
                        spacing="6",
                        direction="row",
                        padding_top="1rem",
                        width="100%"
                    ),
                    value="2"
                ),
                default_value="1"
            ),
            direction="column",
            spacing="4",
            padding="4"
        )
    )
