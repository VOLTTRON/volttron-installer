import reflex as rx
from ..layouts.app_layout import app_layout
from ..model_views import AgentModelView, ConfigStoreEntryModelView
from ..components.header.header import header
from ..components.buttons import icon_button_wrapper, icon_upload
from ..components.form_components import *
from ..components.custom_fields import text_editor

from .platform_page import State as AppState
from .platform_page import Instance
from ..navigation.state import NavigationState

import json, csv, yaml

class AgentConfigState(rx.State):
    # Store reference to working agent
    working_agent: AgentModelView = AgentModelView()
    
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
    def update_agent_detail(self, field: str, value: str, id: str = ""):
        """Update agent details directly"""
        setattr(self.working_agent, field, value)
        
        if id:
            yield rx.set_value(id, value)

    @rx.event
    async def handle_config_store_entry_upload(self, files: list[rx.UploadFile]):
        file = files[0]
        upload_data = await file.read()
        outfile = (rx.get_upload_dir() / file.filename)
        
        with outfile.open("wb") as file_object:
            file_object.write(upload_data)

        result: str = ""
        file_type: str = ""

        if file.filename.endswith('.json'):
            with open(outfile, 'r') as file_object:
                data = json.load(file_object)
                file_type = "JSON"
                result = json.dumps(data, indent=4)
        elif file.filename.endswith('.csv'):
            with open(outfile, 'r') as file_object:
                reader = csv.reader(file_object)
                file_type = "CSV"
                # Handle CSV processing
        else:
            yield rx.toast.error("Unsupported file format")
            return
        
        agent = self.working_agent
        agent.config_store.append(
            ConfigStoreEntryModelView(
                path="",
                data_type=file_type,
                value=result
            )
        )

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


@rx.page(route="/platform/[uid]/agent/[agent_uid]")
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
            rx.heading(AgentConfigState.working_agent.identity, as_="h3"),
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
                            )
                        ),
                        direction="column",
                        spacing="3"
                    ),
                    value="1"
                ),
                rx.tabs.content(
                    rx.flex(
                        rx.upload.root(
                            icon_upload.icon_upload(),
                            id="config_store_entry_upload",
                            accept={
                                "text/csv": [".csv"],
                                "text/json": [".json"]
                            },
                            on_drop=AgentConfigState.handle_config_store_entry_upload
                        ),
                        direction="column"
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