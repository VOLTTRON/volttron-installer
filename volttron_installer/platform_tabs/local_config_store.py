from volttron_installer.components.agent import Agent
from volttron_installer.components.base_tile import BaseTab
from volttron_installer.components.platform_components.platform import Platform
from volttron_installer.modules.remove_from_controls import remove_from_selection
from volttron_installer.views.global_config_store import ConfigForm, Config
from flet import *
from volttron_installer.modules.styles import modal_styles2
from volttron_installer.modules.global_event_bus import global_event_bus
from dataclasses import dataclass
import asyncio
import json
"""This file handles the Agent specific Config Store in the Agent Config Tab inside a Platform's view"""

@dataclass
class LocalConfig(Config):
    # Basically just a copy of Config
    pass

class LocalConfigForm(ConfigForm):
    def __init__(self, config: LocalConfig, page: Page, current_agent: Agent, shared_platform: Platform):
        super().__init__(config, page)
        self.current_agent = current_agent
        self.platform = shared_platform
        print(f"this is our current stuff:\n {self.current_agent.config_store_entries}\n")

        #   # print("what are we actually workign with ", self.current_agent)

    async def save_config(self, e) -> None:
        old_name = self.config.name

        check_overwrite: bool | None = await self.check_overwrite(old_name, self.current_agent.agent_configuration, self.name_field.value)

        if check_overwrite == True:
            global_event_bus.publish("soft_remove", self.config.tile.key)

        elif check_overwrite == False:
            return

        
        # If no existing config with the same name, or if user chooses to overwrite
        self.config.type = self.view_type_radio_group.value
        
        content_data=self.content_value
        try:
            if self.config_mode == "JSON":
                content_data = self.clean_json_string(self.json_content_editor.value)
                
                # Parse the JSON content using json.loads
                parsed_data = json.loads(content_data)
                # print("Parsed Data:", parsed_data)
                # Continue processing `parsed_data`
            # Handle other config modes if necessary
                content_data = parsed_data
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error from saving agent specific config in local_config_store.py: {e}")

        if self.config_mode == "CSV":
            content_data=self.data_table_to_csv()

        self.config.content = content_data
        self.config.name = self.name_field.value

        config_dictionary_appendable = {
            "type" : self.config.type,
            "content" : self.config.content
            }

        # print(check_overwrite)
        if check_overwrite == "rename":
            self.replace_key(self.current_agent.config_store_entries, old_key=old_name, new_key=self.config.name)
        # Update the UI tile content
        self.config.tile.content.controls[0].value = self.config.name
        self.page.update()
        
        # Write to platform
        self.platform.added_agents[self.current_agent.agent_name]["config_store_entries"][self.config.name] = config_dictionary_appendable
        self.changes_finalized(1)


class LocalConfigStoreManagerTab(BaseTab):
    def __init__(self, page: Page, shared_instance: Platform, agent: Agent) -> None:
        self.platform = shared_instance
        self.agent = agent

        self.platform.event_bus.subscribe("display_agent_config_manager", self.display_agent_config_manager)
        self.list_of_configs = Column(
            expand=2,
            controls=[
                Text(f"{self.agent.agent_name}'s config store entires"),
                OutlinedButton(text="Setup a Config", on_click=self.add_new_config)
            ]
        )

        super().__init__(self.list_of_configs, page)
        self.page = page
        global_event_bus.subscribe("tab_change", self.tab_change)
        global_event_bus.subscribe("soft_remove", self.soft_remove)

    def display_agent_config_manager(self, data=None):
        self.tab_change()

    def add_new_config(self, e) -> None:
        self.add_new_tile(self.agent.config_store_entries, "agent_specific_configs", LocalConfig, lambda instance, page: LocalConfigForm(instance, page, current_agent=self.agent, shared_platform = self.platform))
    
    def tab_change(self, selected_tab=None):
        self.refresh_tiles("agent_specific_configs", self.agent.config_store_entries, LocalConfig, lambda instance, page: LocalConfigForm(instance, page, current_agent=self.agent, shared_platform = self.platform))

    # Need to rewrite remove_self function for our usecase
    async def remove_self(self, global_lst: list, file_name: str, instance_attributes: dict):
        if instance_attributes["name"] in self.agent.config_store_entries.keys():
            del self.agent.config_store_entries[instance_attributes["name"]]
        remove_from_selection(self.instance_tile_column, instance_attributes["id"])
        self.tab.content.controls[2].content.controls[0] = Column(expand=3)
        self.page.update()
        self.general_notifier.display_snack_bar("Removed successfully!")

    async def remove_warning(self, global_lst: dict, file_name: str, instance_attributes: dict) -> None:
        loop = asyncio.get_event_loop()
        subject_name = instance_attributes["name"]

        def remove_failed(e):
            self.page.close(modal)
            loop.call_soon_threadsafe(future.set_result, False)

        def remove_continued(e):
            self.page.close(modal)
            loop.call_soon_threadsafe(future.set_result, True)

        modal_contents = Column(
            controls=[
                Text("WARNING!", color="red", size=22),
                Text(f"Are you sure you want to remove {subject_name} permanently?", size=18),
                Row(
                    alignment=MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        OutlinedButton(content=Text("Cancel", color="red"), on_click=remove_failed),
                        OutlinedButton(text="Continue", on_click=remove_continued),
                    ]
                )
            ]
        )

        modal = AlertDialog(
            modal=False,
            bgcolor="#00000000",
            content=Container(
                **modal_styles2(),
                width=400,
                height=170,
                content=modal_contents
            )
        )

        future = loop.create_future()
        self.page.open(modal)
        result = await future
        if result:
            await self.remove_self(global_lst, file_name, instance_attributes)
    
    def remove_warning_wrapper(self, e, global_list, file_name, instance_attributes):
        asyncio.run(self.remove_warning(global_list, file_name, instance_attributes))

    def build_config_store_tab(self) -> Container:
        return self.tab
    