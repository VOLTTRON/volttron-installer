from copy import deepcopy
from dataclasses import dataclass, field
from flet import *
import flet as ft
import json
import yaml
from volttron_installer.views.agent_setup import Agent
from volttron_installer.components import error_modal
from volttron_installer.components.platform_components.platform import Platform
from volttron_installer.modules.remove_from_controls import remove_from_selection
from volttron_installer.modules.styles import modal_styles2
from volttron_installer.modules.validate_field import check_json_field, check_yaml_field

@dataclass
class LocalAgent(Agent):
    platform: Platform
    
    def __post_init__(self) -> None:
        super().__post_init__()
        self.tile.content.controls[1].on_click = lambda e: self.platform.event_bus.publish("agent_removed", self)

    def clone_tile(self) -> None:
        tile = deepcopy(self.tile)
        return tile