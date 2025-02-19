"""
Module to manage Platform Tiles for a monitoring application using the Flet framework.

These objects should have the following properties:
    1. Receive real-time status updates such as health, on/off status, number of agents, any stopped agents
    2. Should route to their own unique page where additional modifications can be made
"""

from flet import *
from typing import Union
from volttron_installer.components.agent import Agent, LocalAgent
from volttron_installer.modules.attempt_to_update_control import attempt_to_update_control
from volttron_installer.modules.dynamic_routes import dynamic_routes
from volttron_installer.modules.global_configs import global_agents
from volttron_installer.components.background import gradial_background
from volttron_installer.components.header import Header
from volttron_installer.modules.write_to_json import dump_to_var, write_to_file
from volttron_installer.platform_tabs.agent_config import AgentConfig
from volttron_installer.platform_tabs.platform_config import PlatformConfig
from volttron_installer.components.platform_components.platform import Platform

class PlatformTile:
    """
    Class to represent and manage a Platform Tile.

    Attributes:
        container (Container): The container that holds the platform tile.
        shared_instance (Platform): Shared instance of the Platform class containing platform information.
    """
    def __init__(self, container: Container, shared_instance: Platform) -> None:
        """
        Initialize a PlatformTile instance.
        """
        self.platform = shared_instance

        # Subscribe to platform events
        self.platform.event_bus.subscribe("update_ui", self.update_platform_tile_ui)
        self.platform.event_bus.subscribe("agent_appended", self.forward_agent_appended)
        self.platform.event_bus.subscribe("agent_removed", self.forward_agent_removed)
        self.platform.event_bus.subscribe("load_platform", self.load_agent_ui)
        self.platform.event_bus.subscribe("platform_title_update", self.platform_title_update)

        self.home_container = container
        self.platform_tile = self.build_tile()


        # Initialize Platform Config tab
        self.platform_config_tab = PlatformConfig(
            self.platform, # passing shared instances
        ).platform_config_view()

        # Initialize Agent Config tab
        self.agent_config_tab = AgentConfig(
            self.platform,
        ).build_agent_config_tab()

        # Add route to dynamic routes dynamically
        view = self.platform_view()
        dynamic_routes[self.platform.generated_url] = view

    def platform_title_update(self, data=None) -> None:
        """Subscribed to signal `platform_title_update`"""
        self.platform_tile.content.controls[0].controls[0].content.controls[0].value = self.platform.title
        attempt_to_update_control(self.platform_tile.content.controls[0].controls[0])

    def load_agent_ui(self, data=None):
        """Subscribed to signal `load_platform`"""
        agents = self.platform.added_agents.keys()
        for name in agents:
            loaded_agent = LocalAgent(
                agent_name=name,
                identity=self.platform.added_agents[name]["identity"],
                agent_path=self.platform.added_agents[name]["agent_path"],
                agent_configuration=self.platform.added_agents[name]["agent_configuration"],
                config_store_entries=self.platform.added_agents[name]["config_store_entries"],
                platform=self.platform
            )
            self.platform.event_bus.publish("append_your_agent", loaded_agent)

    def forward_agent_removed(self, agent: Agent) -> None:
        agent_name: str = agent.agent_name
        del self.platform.added_agents[agent_name]
        self.platform.event_bus.publish("remove_your_agent", agent)

    def forward_agent_appended(self, agent_name: str) -> None:
        working_agent: dict = global_agents[agent_name]
        self.platform.added_agents[agent_name] = global_agents[agent_name]
        agent = LocalAgent(
            agent_name=agent_name, 
            identity=working_agent["identity"], 
            agent_path=working_agent["agent_path"], 
            agent_configuration=working_agent["agent_configuration"], 
            config_store_entries=working_agent["config_store_entries"], 
            platform=self.platform
            )
        self.platform.event_bus.publish("append_your_agent", agent)

    def get_background_color(self):

        return "#9d9d9d" if self.platform.activity == "ON" else colors.with_opacity(0.65, "#9d9d9d")

    def get_text_color(self):

        return "white" if self.platform.activity == "ON" else colors.with_opacity(0.65, "white")

    def get_status_color(self):

        return "#00ff00" if self.platform.activity == "ON" else colors.with_opacity(0.65, "#ff0000")

    def update_platform_tile_ui(self, e=None):

        self.platform_tile.bgcolor = self.get_background_color()

        # Handling Platform Tile Title
        self.platform_tile.content.controls[0].controls[1].content.controls[0].value = self.get_status()
        self.platform_tile.content.controls[1].controls[1].content.controls[0].value = self.get_state()
        self.platform_tile.content.controls[-1].controls[1].content.controls[0].value = len(self.platform.added_agents)
        # Iterate over each row in platform_tile's content
        for row_index, row in enumerate(self.platform_tile.content.controls):
            # Iterate over each container inside the current row
            for container_index, formatted_stat in enumerate(row.controls):
                # Check if the container content is a Column
                if isinstance(formatted_stat.content, Column):
                    # Iterate over each Text control within the Column
                    for text_index, text_control in enumerate(formatted_stat.content.controls):
                        if isinstance(text_control, Text):
                            text_control.color = self.get_text_color()
                            # if row_index == 0 and container_index == 0:
                            #     text_control.value = self.get_status()
                            # elif row_index == 1 and container_index == 0:
                            #     text_control.value = self.get_state()
                            # elif row_index == 2 and container_index == 0:
                            #     text_control.value = str(len(self.platform.added_agents))

        # Override blanket re-styling of text
        self.platform_title_update()

    def get_status(self) -> str:
        status = "ON" if self.platform.running == True else "OFF"
        if status == "ON":
            # Method to update platform tile UI
            pass 
        return status

    def get_state(self) -> str:
        return "Un-deployed" if self.platform.deployed == False else "Deployed"

    def build_tile(self) -> Container:
        def format_tile_ui(
            col1_text: Text, col2_text: Text,
            col2_padding: Union[Padding, int] = 0, 
            col1_expand: Union[int, bool] = False,
            col2_expand: Union[int, bool] = False) -> Row:
            return  Row(
                        controls=[
                            Container(
                                expand=col1_expand,
                                # bgcolor=colors.with_opacity(0.3, "red"),
                                content=Column(
                                    controls=[
                                        col1_text,
                                    ],
                                    alignment=CrossAxisAlignment.START
                                ),
                            ), 
                            Container(
                                padding=col2_padding,
                                expand=col2_expand,
                                # bgcolor=colors.with_opacity(0.3, "blue"),
                                content=Column(
                                    controls=[
                                        col2_text,
                                    ],
                                    alignment=CrossAxisAlignment.END
                                ),
                            )
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                    )

        counter = dump_to_var("tile_id")
        counter =+ 1
        write_to_file("tile_id", counter)
        tile_id_key = f"platform {counter}"

        self.platform.tile_key = tile_id_key
        return Container(
            key= tile_id_key,
            width=150,
            height=150,
            border_radius=25,
            padding=padding.all(10),
            bgcolor=self.get_background_color(),
            on_click=lambda e: self.platform.page.go(self.platform.generated_url), # Routes to individualized page for managing platform
            content=Column(
                controls=[
                    # Title and running status(OFF/ON)
                    format_tile_ui(Text(self.platform.title, color=self.get_text_color()), Text(value=f"{self.get_status()}", color=self.get_status_color())),
                    # Row(
                    #     controls=[
                    #         Container(
                    #             expand=3,
                    #             bgcolor=colors.with_opacity(0.3, "red"),
                    #             content=Column(
                    #                 controls=[
                    #                     Text(self.platform.title, color=self.get_text_color()),
                    #                 ],
                    #                 alignment=CrossAxisAlignment.START
                    #             ),
                    #         ), 
                    #         Container(
                    #             padding=padding.only(left=5),
                    #             expand=1,
                    #             bgcolor=colors.with_opacity(0.3, "blue"),
                    #             content=Column(
                    #                 controls=[
                    #                     Text(value=f"{self.platform.activity}", color=self.get_status_color()),
                    #                 ],
                    #                 alignment=CrossAxisAlignment.END
                    #             ),
                    #         )
                    #     ],
                    #     alignment=MainAxisAlignment.SPACE_BETWEEN,
                    #     spacing=30,
                    # ),

                    # State 
                    format_tile_ui(Text("Status", color=self.get_text_color()), Text(self.get_state(), color=self.get_text_color())),
                    # Row(
                    #     controls=[
                    #         Container(
                                
                    #             bgcolor=colors.with_opacity(0.3, "red"),
                    #             content=Column(
                    #                 controls=[
                    #                     Text("Status", color=self.get_text_color()),
                    #                 ],
                    #                 alignment=CrossAxisAlignment.START
                    #             ),
                    #         ), 
                    #         Container(
                    #             # padding=padding.only(left=5),
                    #             bgcolor=colors.with_opacity(0.3, "blue"),
                    #             content=Column(
                    #                 controls=[
                    #                     Text("Deployed", color=self.get_text_color()),
                    #                 ],
                    #                 alignment=CrossAxisAlignment.END
                    #             ),
                    #         )
                    #     ],
                    #     alignment=MainAxisAlignment.SPACE_BETWEEN,
                    # ),

                    # Running Agents
                    format_tile_ui(Text("Running Agents", color=self.get_text_color()), Text("0", color=self.get_text_color())),
                    # Row(
                    #     controls=[
                    #         Container(
                                
                    #             bgcolor=colors.with_opacity(0.3, "red"),
                    #             content=Column(
                    #                 controls=[
                    #                     Text("Running Agents", color=self.get_text_color()),
                    #                 ],
                    #                 alignment=CrossAxisAlignment.START
                    #             ),
                    #         ), 
                    #         Container(
                    #             # padding=padding.only(left=5),
                    #             bgcolor=colors.with_opacity(0.3, "blue"),
                    #             content=Column(
                    #                 controls=[
                    #                     Text("0", color=self.get_text_color()),
                    #                 ],
                    #                 alignment=CrossAxisAlignment.END
                    #             ),
                    #         )
                    #     ],
                    #     alignment=MainAxisAlignment.SPACE_BETWEEN,
                    # ),

                    # Healthy Agents
                    format_tile_ui(Text("Healthy Agents", color=self.get_text_color()), Text("0", color=self.get_text_color()))
                    # Row(
                    #     controls=[
                    #         Container(
                                
                    #             bgcolor=colors.with_opacity(0.3, "red"),
                    #             content=Column(
                    #                 controls=[
                    #                     Text("Healthy Agents", color=self.get_text_color()),
                    #                 ],
                    #                 alignment=CrossAxisAlignment.START
                    #             ),
                    #         ), 
                    #         Container(
                    #             # padding=padding.only(left=5),
                    #             bgcolor=colors.with_opacity(0.3, "blue"),
                    #             content=Column(
                    #                 controls=[
                    #                     Text("0", color=self.get_text_color()),
                    #                 ],
                    #                 alignment=CrossAxisAlignment.END
                    #             ),
                    #         )
                    #     ],
                    #     alignment=MainAxisAlignment.SPACE_BETWEEN,
                    # ),
                ]
            )
        )

    def build_card(self) -> Container:

        return self.platform_tile

    def platform_view(self) -> View:

        # Initializing the header and background
        header = Header(self.platform, "/").return_header()
        background_gradient = gradial_background()
        return View(
            self.platform.generated_url,
            controls=[
                Stack(
                    controls=[
                        background_gradient,
                        Column(
                            controls=[
                                header,
                                Tabs(
                                    selected_index=0,
                                    animation_duration=300,
                                    tabs=[
                                        Tab(
                                            text="Platform Config",
                                            content=self.platform_config_tab
                                        ),
                                        Tab(
                                            text="Agent Config",
                                            content=Column(
                                                controls=[    
                                                    self.agent_config_tab
                                                ],
                                                scroll=ScrollMode.ADAPTIVE,
                                            )
                                        )
                                    ],
                                    expand=1,
                                )
                            ]
                        ),
                    ],
                expand=True
                )
            ],
            padding=0
        )

# Container to hold platform tiles
platform_tile_container = Row(wrap=True)
