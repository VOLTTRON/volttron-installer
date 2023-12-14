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

Pages.HOME.value.module = show_home