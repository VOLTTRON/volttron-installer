from logging import config
from typing import Union
from volttron_installer.components.base_tile import BaseForm, BaseTab, BaseTile
from volttron_installer.modules.prettify_string import prettify_json, prettify_yaml
from volttron_installer.modules.attempt_to_update_control import attempt_to_update_control
from volttron_installer.modules.show_selected_tile import show_selected_tile
from volttron_installer.modules.global_configs import global_agents, global_drivers
from volttron_installer.modules.global_event_bus import global_event_bus
from volttron_installer.modules.remove_from_controls import remove_from_selection
from volttron_installer.modules.styles import modal_styles2
from volttron_installer.modules.populate_dropdowns import numerate_configs_dropdown
from volttron_installer.modules.validate_field import check_yaml_field, check_json_field, check_format
from volttron_installer.components.error_modal import error_modal
from volttron_installer.components.template_editor_modal import ConfigFormTemplate, ConfigTemplate
from dataclasses import dataclass, field
from volttron_installer.components.upload_config import ConfigFilePicker
import json
import yaml
from flet import *

from volttron_installer.modules.write_to_json import write_to_file

key_constructor =[
    "agent_name",
    "identity",
    "agent_path",
    "agent_configuration"
]

@dataclass
class Agent(BaseTile):
    agent_name: str
    identity: str
    agent_path: str
    agent_configuration: str
    config_store_entries: str | dict

    tile: Container = field(init=False)
    
    def __post_init__(self):
        super().__init__(self.agent_name)  # Initialize BaseTile with agent_name
        self.tile = self.build_agent_tile()

    def build_agent_tile(self) -> Container:
        return self.build_tile()  # Calls BaseTile's build_tile method


class AgentForm(BaseForm):
    def __init__(self, agent, page: Page):
        self.page=page
        self.agent_name_field = TextField(on_change=self.validate_fields)
        self.identity_field = TextField(on_change=self.validate_fields)
        self.agent_path_field = TextField(on_change=self.validate_fields)

        #NOTE:
        # handling the file picker and events and stuff of that nature 
        self.pick_config_file = ConfigFilePicker(self.page)
        
        self.load_configs_btn = OutlinedButton(
                                    icon=icons.UPLOAD_FILE, 
                                    on_click= lambda e: self.pick_config_file.launch_file_picker(allowed_extensions=["yaml", "json"])
                                )
        
        self.agent_configuration_field = TextField(
                                hint_text="Input custom YAML or JSON",
                                on_change=self.validate_fields,
                                multiline=True,
                                text_style=TextStyle(font_family="Consolas"),
                            )
        
        global_event_bus.subscribe("update_global_ui", self.update_ui)
        global_event_bus.subscribe("agent_config_store_edit", self.config_entry_edited)
        global_event_bus.subscribe("added_config_template", self.update_template_dropdown)

        self.config_dropdown: Dropdown = numerate_configs_dropdown()
        self.config_dropdown.value = "None"
        attempt_to_update_control(self.config_dropdown)
        self.config_dropdown.on_change = "" # method 
        self.config_name_field: TextField = TextField(
                                                label="Entry Name",
                                                on_change=self.validate_template_addition
                                            )
        self.add_template_button = OutlinedButton(on_click=self.save_config_store_entries, disabled=True, text="Add")
        self.modal_content = Column(
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                        controls=[
                            Text("Add Template", size=20),
                            self.config_dropdown,
                            self.config_name_field,
                            Container(
                                margin=margin.only(bottom=-20),
                                padding=padding.only(left=25, right=25),
                                alignment=alignment.bottom_center,
                                content=Row(
                                    controls=[
                                        OutlinedButton(on_click=lambda e: self.page.close(self.modal),
                                                    content=Text("Cancel", color="red")),
                                        self.add_template_button
                                    ],
                                    alignment=MainAxisAlignment.SPACE_BETWEEN
                                )
                            )
                        ]
                    )
        
        self.modal = AlertDialog(
                        modal = False,
                        bgcolor="#00000000",
                        content=Container(
                            **modal_styles2(),
                            width=400,
                            height=250,
                            content=self.modal_content
                        )
                    )

        self.added_config_entries_container = Container(
            margin=4,
            border_radius= 7,
            padding=5, 
            key="pass",
            height=1000,
            #bgcolor=colors.with_opacity(0.45, "black"),
            content=Row(
                controls=[
                    Column(
                        # [
                        #     Text("Total Entries:")
                        # ],
                    ),
                    Container(
                        content = Column(

                        )
                    ) # COntainer for field haha
                ],
                spacing=20
            )
        )

        form_fields = {
            "Name" : self.agent_name_field,
            "Identity" : self.identity_field,
            "Agent Path" : self.agent_path_field,
            "Agent Configuration" : Row(controls=[self.agent_configuration_field, self.load_configs_btn]),
            "Config Store Entries" : OutlinedButton(text="Add", on_click=lambda e: self.page.open(self.modal)),
            "store entries container" : self.added_config_entries_container
        }

        super().__init__(page, form_fields)
        self.agent: Agent = agent
        self.agent_config_validity = True
        self.agent_config_type: str | "YAML" | "JSON" = ""
        self.added_config_store_entries: dict = self.load_config_store_entries()
        self.__post_init__()

    def update_template_dropdown(self, data= None) -> None:
        # print("We gotta be updating this dropdown type shi")
        self.modal_content.controls[1] = numerate_configs_dropdown()
        self.modal_content.controls[1].value = "None"
        attempt_to_update_control(self.config_dropdown)
        attempt_to_update_control(self.modal_content.controls[1])
        # print(f"have we updated? {self.modal_content.controls[1].options}")

    def load_config_store_entries(self) -> dict:
        try:
            if isinstance(self.agent.config_store_entries, str):
                self.agent.config_store_entries = {}
            config_store_entries: dict = self.agent.config_store_entries
            return config_store_entries
        except:
            return {}

    def validate_template_addition(self, e) -> None:
        """Because the Name field cannot be blank, we need to stop the user
        from submitting a blank name"""
        if self.config_name_field.value != "":
            self.add_template_button.disabled=False
        else:
            self.add_template_button.disabled=True
        attempt_to_update_control(self.add_template_button)

    # Loads the saved data
    def __post_init__(self):
        tiles_to_append = []
        for i in self.added_config_store_entries.keys():
            tiles_to_append.append(self.create_added_entry_tile(title=i, empty_config=False))
        self.added_config_entries_container.content.controls[0].controls.extend(tiles_to_append)
        attempt_to_update_control(self.added_config_entries_container)

        config_type = check_format(str(self.agent.agent_configuration))
        if config_type == "JSON":
            self.agent_configuration_field.value = prettify_json(self.agent.agent_configuration)
        elif config_type == "YAML":
            self.agent_configuration_field.value = prettify_yaml(self.agent.agent_configuration)
        attempt_to_update_control(self.agent_configuration_field)

    def save_config_store_entries(self, e) -> None:
        # on dropdown change, fill out the text field with value as a default name
        title: str = self.config_name_field.value
        if self.config_dropdown.value == "None":
            self.added_config_entries_container.content.controls[0].controls.append(self.create_added_entry_tile(title, empty_config=True))
        elif self.config_dropdown.value not in self.added_config_store_entries:
            self.added_config_store_entries[title] = global_drivers[self.config_dropdown.value]
            self.added_config_entries_container.content.controls[0].controls.append(self.create_added_entry_tile(title, empty_config=False))
        attempt_to_update_control(self.added_config_entries_container)
        self.page.close(self.modal)

    def update_ui(self, var = None)-> None:
        self.config_dropdown = numerate_configs_dropdown()
        attempt_to_update_control(self.config_dropdown)

    def create_added_entry_tile(self, title: str, empty_config: bool) -> Container:
        #debug 
        # # print("sooooo", title, self.added_config_store_entries, self.added_config_store_entries[title])
        # # print("type of title config", type(self.added_config_store_entries[title]))
        # print("this is the added config name", title)
        if empty_config:
            template_instance = ConfigTemplate(name=title, content="", type="")
            template_form_instance = ConfigFormTemplate(template_instance, self.page, self.agent)
        else:
            template_instance = ConfigTemplate(name=title, content=self.added_config_store_entries[title]["content"], type=self.added_config_store_entries[title]["type"])
            template_form_instance = ConfigFormTemplate(template_instance, self.page, self.agent)
        tile = template_instance.tile
        tile.on_click = lambda e: self.select_config_entry(e, template_form_instance, tile_container=self.added_config_entries_container.content.controls[0])
        tile.content.controls[1].on_click = lambda e: self.remove_from_added_entries(title, id=tile.key)
        return tile

    def display_editor(self, form: ConfigFormTemplate) -> None:
        form_view = form.build_form()
        form_view.scroll = None
        form_view.expand = True
        self.added_config_entries_container.content.controls[1] = form_view
        attempt_to_update_control(self.added_config_entries_container)

    def select_config_entry(self, e, form: ConfigFormTemplate, tile_container: Container) -> None:
        self.display_editor(form)
        show_selected_tile(e, tile_container)
        self.page.update()

    def remove_from_added_entries(self, title: str, id: str) -> None:
        del self.added_config_store_entries[title]
        remove_from_selection(self.added_config_entries_container.content.controls[0], id)

    def config_entry_edited(self, new_config: dict) -> None:
        pass
        # if next(iter(name_config_arg.keys())) == self.agent.agent_name:

        #     # Save the config_name to a variable
        #     config_name: str = next(iter(name_config_arg[self.agent.agent_name]))

        #     # Write to the global_agents dictionary
        #     self.agent.config_store_entries[config_name] = [name_config_arg[self.agent_name_field]]
        #     global_agents[self.agent.agent_name]["config_store_entries"][config_name] = [name_config_arg[self.agent.agent_name][config_name]]
            
        #     # should enable save button for main form

        #     # Save our changes to a JSON file
        #     self.write_to_file("agents", global_agents)
        # return

    def validate_fields(self, e) -> None:
        # Implement field validation logic and toggle submit button state.
        fields = [self.form_fields[i] for i in self.form_fields.keys() if isinstance(self.form_fields[i], TextField)]
        valid = all(field.value for field in fields)

        if self.agent_config_validity == False:
            self.toggle_submit_button(False)
        else:
            self.toggle_submit_button(valid)

    def check_agent_config_field(self) -> bool:
        valid_config: Union[bool, str, dict]
        self.agent_configuration_field.value = str(self.agent_configuration_field.value)
        
        if check_json_field(self.agent_configuration_field):
            self.agent_config_type = "JSON"
            # print("i am passing as json", self.agent_configuration_field.value)
            valid_config = json.loads(self.agent_configuration_field.value)
            return valid_config
        elif check_yaml_field(self.agent_configuration_field):
            # print("\ni am passing as yaml:\n", self.agent_configuration_field.value)
            self.agent_config_type = "YAML"
            valid_config = yaml.safe_load(self.agent_configuration_field.value)
            # print("\nThis is the yaml im verifying:\n",valid_config)
            return valid_config
        else:
            self.page.open(error_modal())
            return False
        
    async def save_config(self, e) -> None:
        old_name = self.agent.agent_name
        check_overwrite = await self.check_overwrite(self.agent.agent_name, global_agents, self.agent_name_field.value)

        # check_overwrite: bool | None = await self.detect_conflict(global_agents, self.agent_name_field.value, self.agent.agent_name)

        if check_overwrite == True:
            global_event_bus.publish("soft_remove", self.agent.tile.key)

        elif check_overwrite == False:
            return

        
        # print("\n-------------------------------------------------\nthe saving process is begininig\n")
        valid_config: bool | dict | str = self.check_agent_config_field()
        if valid_config == False:
            return
        
        # print("\nThis is my freshly validated config:\n", valid_config)

        if self.agent_config_type == "YAML":
            # Reconvert to YAML string to preserve format for saving/displaying
            valid_config_str = yaml.dump(valid_config, sort_keys=False, default_flow_style=False)
            valid_config = valid_config_str
            # print("\nThis is my freshly validated YAML config:\n", valid_config_str)
        else:
            # print("\nThis is my freshly validated JSON config:\n", valid_config)
            pass




        # Save field values to agent attributes
        self.agent.identity = self.identity_field.value
        self.agent.agent_path = self.agent_path_field.value
        self.agent.agent_configuration = valid_config
        self.agent.agent_name = self.agent_name_field.value

        dictionary_appendable = {
            "identity" : self.agent.identity,
            "agent_path" : self.agent.agent_path,
            "agent_configuration" : valid_config,
            "config_store_entries" : self.added_config_store_entries
        }

        # print("\nThis is what im writing to file:\n", valid_config)

        if check_overwrite == "rename":
            self.replace_key(global_agents, old_key=old_name, new_key=self.agent.agent_name)
        global_agents[self.agent.agent_name] = dictionary_appendable

        self.agent.tile.content.controls[0].value = self.agent.agent_name
        attempt_to_update_control(self.page)
        self.write_to_file("agents", global_agents)
        update_global_ui()

class AgentSetupTab(BaseTab):
    def __init__(self, page: Page) -> None:
        self.list_of_agents = Column(
            expand=2,
            controls=[
                OutlinedButton(text="Setup an Agent", on_click=self.add_new_agent)
            ]
        )
        super().__init__(self.list_of_agents, page)
        self.page = page
        self.agent_tab_view = self.tab

        global_event_bus.subscribe("tab_change", self.tab_change)

    def tab_change(self, selected_tab):
        self.refresh_tiles("agents", global_agents, Agent, AgentForm)

    def add_new_agent(self, e) -> None:
        self.add_new_tile(global_agents, "agents", Agent, AgentForm)

    def build_agent_setup_tab(self) -> Container:
        return self.agent_tab_view

def update_global_ui():
    global_event_bus.publish("update_global_ui", None)