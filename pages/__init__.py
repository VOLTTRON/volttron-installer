from dataclasses import dataclass
from enum import Enum
from typing import Callable

from nicegui import ui

@dataclass
class PageDetails:
    name: str
    title: str
    uri: str
    module: Callable = None

class Pages(Enum):
    HOME = PageDetails("home", "Home", "/")
    MACHINES = PageDetails("machines", "Machines", "/machines")
    INSTANCES = PageDetails("instances", "Instances", "/instances")
    EDIT_INSTANCE = PageDetails("edit_instance", "Edit Instance", "VARIES") # uri varies
    DEPLOY = PageDetails("deploy", "Deploy", "VARIES") # uri varies
    CONFIG = PageDetails("config", "Configuration", "/config")
    EDIT_CONFIG = PageDetails("edit_config", "Edit Configuration", "VARIES") # uri varies

def show_global_header(page: PageDetails):
    header_items = {
        "Home": "/", 
        "Machines": "/machines", 
        "Instances": "/instances"
        }
    
    with ui.header():
        with ui.row():
            for title, target in header_items.items():
                if title == page.name:
                    ui.link(title, target).style("color: white; text-decoration: none; font-size: 16px; font-weight: bold")
                else: 
                    ui.link(title, target).style("color: white; text-decoration: none; font-size: 16px")

from .home import show_home
from .machines import show_machines
from .instances import show_instances
from .edit_instance import show_edit_instance
from .deploy import show_deploy_page
from .config import show_config_list
from .edit_config import show_config

Pages.HOME.value.module = show_home
Pages.MACHINES.value.module = show_machines
Pages.INSTANCES.value.module = show_instances
Pages.EDIT_INSTANCE.value.module = show_edit_instance
Pages.DEPLOY.value.module = show_deploy_page
Pages.CONFIG.value.module = show_config_list
Pages.EDIT_CONFIG.value.module = show_config