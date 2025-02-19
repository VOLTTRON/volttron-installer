# home.py

import pprint
from flet import *

from typing import Callable

import logging

from volttron_installer.modules import attempt_to_update_control
from volttron_installer.modules.global_configs import find_dict_index
from volttron_installer.modules.remove_from_controls import remove_from_selection

_log = logging.getLogger(__name__)

import random
import string


from volttron_installer.views import agent_setup, hosts_tab, global_config_store
from volttron_installer.components.platform_tile import platform_tile_container
from volttron_installer.modules.global_configs import platforms
from volttron_installer.components.background import gradial_background
from volttron_installer.components.platform_tile import PlatformTile
from volttron_installer.components.platform_components.platform import Platform, ObjectCommunicator
from volttron_installer.modules.global_event_bus import global_event_bus


refreshed = False

# Helper function to generate a random URL path
def generate_random_path(length=7) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Generates until URL is unique
def generate_URL() -> str:
    platforms_added = platforms.keys()
    while True:
        new_url = generate_random_path()
        generated_url = f"/{new_url}"
        if generated_url not in platforms_added:
            return generated_url

def numerate_amount_of_platforms() -> str:
    platform_number = len(platforms)
    return f"P{platform_number + 1}"

def home_view(page: Page) -> View:
    from volttron_installer.views import InstallerViews as vi_views

    def remove_platform(tile_key: str) -> None:
        remove_from_selection(platform_tile_container, tile_key)
        attempt_to_update_control.attempt_to_update_control(platform_tile_container)

    def refresh_platforms() -> None:
        global refreshed
        if refreshed:
            return
        for uid in platforms.keys(): #.keys()
            working_platform = platforms[uid] # platforms json dump var
            event_bus = ObjectCommunicator()
            init_platform = Platform(working_platform["title"], page, uid, event_bus, global_event_bus)
            init_platform.added_hosts = working_platform["host"]
            init_platform.address= working_platform["address"]
            init_platform.ports = working_platform["ports"]
            init_platform.added_agents = working_platform["agents"]
            init_platform.running = working_platform["running"] 
            init_platform.deployed = working_platform["deployed"] 

            pprint.pprint(working_platform)

            # Load tile on platform tab
            init_platform_tile = PlatformTile(platform_tile_container, init_platform)
            platform_tile_container.controls.append(init_platform_tile.build_card())
            page.update()
            init_platform.load_platform()   
            refreshed= True

    def add_platform_tile(e) -> None:
        # Creates a single instance of ObjectCommunicator to be used throughout the whole platform
        event_bus = ObjectCommunicator()
        
        # Creates a shared platform instance with that same ObjectCommunicator
        shared_platform_instance = Platform(numerate_amount_of_platforms(), page, generate_URL(), event_bus, global_event_bus)
        platform_tile = PlatformTile(platform_tile_container, shared_platform_instance)
        
        # Add platform tile to container
        platform_tile_container.controls.append(platform_tile.build_card())
        page.update()

        # Change the selected index of the tabs to 0
        tabs_reference.selected_index = 2
        tabs_reference.update()
    
    # Minor TODO: the signal of tab_change is redundant, should be called
    # `refresh_form_tiles` or something like that, doesnt even need data input
    def tab_change(selected_index):
        global_event_bus.publish("tab_change", selected_index)

    if refreshed == False:
        refresh_platforms()


    global_event_bus.subscribe("remove_platform", remove_platform)

    # Initialize tabs
    agent_setup_tab = agent_setup.AgentSetupTab(page).build_agent_setup_tab()
    host_config_tab = hosts_tab.HostTab(page).build_host_setup_tab()
    config_store_tab = global_config_store.ConfigStoreManagerTab(page).build_config_store_tab()

    background_gradient = gradial_background()

    # Create the view and Tabs while assigning a reference
    tabs_reference = Tabs(
        selected_index=0,
        animation_duration=300,

        # Again, should just publish refresh_form_tiles signal or something 
        on_change= lambda e: tab_change(e.control.selected_index),
        tabs=[
            Tab(
                text="Hosts",
                content=host_config_tab
            ),
            Tab(
                text="Agent Setup",
                content=agent_setup_tab
            ),
            Tab(
                text="Platforms",
                content=Container(  # main view of all the platform tiles
                    padding=padding.only(left=15, right=0, top=50, bottom=15),
                    content=Column(
                        scroll=ScrollMode.AUTO,
                        controls=[platform_tile_container]
                    )
                )
            ),
            Tab(
                text="Config Store Templates",
                content=config_store_tab
            )
        ],
        expand=1
    )

    view = View(
        "/",
        controls=[
            Stack(
                controls=[
                    background_gradient,
                    Column(
                        controls=[
                            Container(  # header
                                padding=padding.only(left=20, right=20),
                                content=Row(
                                    controls=[
                                        Text("Overview", size=60, color="white"),
                                        IconButton(
                                            icon=icons.ADD,
                                            tooltip="Add platform",
                                            icon_color="white",
                                            icon_size=40,
                                            on_click=add_platform_tile
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                                ),
                            ),
                            tabs_reference
                        ],
                        expand=True
                    ),
                ],
                expand=True
            )
        ],
        padding=0
    )
    return view


global_event_bus.publish("tab_change", None) # trying to populate everything ONCE IT LOADS
