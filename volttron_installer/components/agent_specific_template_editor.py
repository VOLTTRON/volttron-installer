from flet import Page
from volttron_installer.modules import attempt_to_update_control
from volttron_installer.views.global_config_store import Config, ConfigForm, ConfigStoreManagerTab
from volttron_installer.modules.global_event_bus import global_event_bus
from volttron_installer.modules.global_configs import global_agents
from volttron_installer.modules.styles import modal_styles2
from dataclasses import dataclass
from flet import *
import json

@dataclass
class ConfigTemplate(Config): # basically just a copy of Config because I like the functionality
    pass

class ConfigFormTemplate(ConfigForm):
    def __init__(self, config: ConfigTemplate, page: Page, agent):
        super().__init__(config, page)
        self.name_field.value = self.config.name
        self.agent=agent
        self.agent_name = self.agent.agent_name
    
    async def save_config(self, e) -> None:
        old_name = self.config.name

        check_overwrite: bool | None = await self.check_overwrite(old_name, self.agent.config_store_entries, self.name_field.value)

        if check_overwrite == True:
            global_event_bus.publish("soft_remove", self.config.tile.key)

        elif check_overwrite == False:
            return
        
        self.config.type = self.view_type_radio_group.value

        content_data=self.content_value
        if self.config_mode == "JSON":
            content_data = self.clean_json_string(self.json_content_editor.value)
            
            try:
                content_data = json.loads(content_data)  # Safely convert to a dictionary
            except json.JSONDecodeError as e:
                # print(f"Error parsing JSON: {e}")
                content_data = {}  # Handle this case as needed (e.g., set a default or show an error)

        elif self.config_mode == "CSV":
            content_data = self.data_table_to_csv()
            content_data =  str(content_data)

        self.config.content = content_data
        self.config.name = self.name_field.value
        config_dictionary_appendable = {
                "type" : self.config.type,
                "content" : self.config.content
            }
        
        self.config.tile.content.controls[0].value = self.config.name
        attempt_to_update_control.attempt_to_update_control(self.config.tile)
        # throw self.config.name and config_dictionary_appendable into the
        # event bus and create a new or replace an existing template
        self.agent.config_store_entries[self.config.name] = config_dictionary_appendable

        #TODO: put this in the agetn config tab in platform and stuff
        self.changes_finalized(1)
        # print("ioh yeahh we just saved a new agentsepcific configgg\n,ohhhh ", self.agent.config_store_entries)