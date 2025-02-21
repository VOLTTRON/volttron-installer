"""
SO FAR, A COMPLETELY USELESS FILE BECAUSE I TRIED TO BREAK APART THE 
OVERVIEW TABS OF `agent_setup.py`, `global_config_store.py`, AND `hosts_tab.py`
BECAUSE THEY PRACTICALLY ARE JUST COPY AND PASTES OF EACHOTHER AND IT BOTHERS ME
"""

from dataclasses import dataclass, field
from flet import *
from volttron_installer.components.default_tile_styles import build_default_tile
from volttron_installer.modules.create_field_methods import field_pair, divide_fields
from volttron_installer.modules.global_configs import find_dict_index
from volttron_installer.modules.remove_from_controls import remove_from_selection

@dataclass
class CommonEntity:
    counter = 0  # class variable to ensure unique ids
    id_key : int = field(init=False)

    def __post_init__(self):
        self.id_key = self.__class__.counter
        self.__class__.counter += 1

class CommonForm:
    def __init__(self, page: Page, entity, tile: Container, list_of_entities: Column, view: Container, global_list, write_to_file):
        self.page = page
        self.entity = entity
        self.tile = tile
        self.list_of_entities = list_of_entities
        self.view = view
        self.global_list = global_list
        self.write_to_file = write_to_file

        self.tile.content.controls[1].on_click = self.remove_self

    def remove_self(self, e) -> None:
        index = find_dict_index(self.global_list, self.entity.identifier())
        if index is not None:
            self.global_list.pop(index)
            self.write_to_file()
        # else:
            # # print("The entity you are trying to remove hasn't been properly registered yet.")
        remove_from_selection(self.list_of_entities, self.entity.id_key)
        self.view.content.controls[2] = Column(expand=3)
        self.page.update()

    def validate_submit(self, e, required_fields) -> None:
        self.submit_button.disabled = not all(field.value for field in required_fields)
        self.submit_button.update()
    
    def build_form(self, formatted_fields) -> Column:
        return Column(
            expand=3,
            controls=[
                *formatted_fields,
                self.submit_button,
            ]
        )

@dataclass
class Host(CommonEntity):
    host_id: str
    ssh_sudo_user: str
    identity_file: str
    ssh_ip_address: str
    ssh_port: str

    def build_tile(self) -> Container:
        return build_default_tile(self.host_id)

    def identifier(self):
        return self.host_id

@dataclass
class Agent(CommonEntity):
    agent_name: str
    identity: str
    agent_path: str
    agent_configuration: str

    def build_tile(self) -> Container:
        return build_default_tile(self.agent_name)

    def identifier(self):
        return self.agent_name
