"""
Module to manage the platform configuration in a platform management application using the Flet framework.
"""

from volttron_installer.components.platform_components.platform import Platform
from volttron_installer.components.agent import Agent, LocalAgent
from volttron_installer.modules.attempt_to_update_control import attempt_to_update_control
from volttron_installer.modules.create_field_methods import field_pair, divide_fields
from volttron_installer.modules.populate_dropdowns import numerate_host_dropdown, numerate_agent_dropdown
from volttron_installer.modules.global_configs import global_hosts
from flet import *

from volttron_installer.modules.remove_from_controls import remove_from_selection


class PlatformConfig:
    """
    Class to represent and manage the platform configuration.

    Attributes:
        name_field (TextField): The text field for the platform name.
        addresses_field (TextField): The text field for platform addresses.
        ports_field (TextField): The text field for platform ports.
        shared_instance (Platform): Shared instance of the Platform class containing platform information.
        platform_config_agent_column (Column): Column to hold the platform configuration agents.
        agent_config_column (Column): Column to hold the agent configuration.

        HEADS UP THESE ARE ALL USELESS WE ONLY NEEDED TO PASS THE ``shared_instance`` AND ``agent_config_column``
        BECAUSE WE CAN JUST ASSIGN OUR OWN TEXT FIELDS ANS SUCH
    """
    def __init__(self,
                 shared_instance: Platform,
                 ) -> None:
        
        # Initialize the shared instance
        self.platform = shared_instance
        
        # Subscribe to events
        self.platform.event_bus.subscribe("update_global_ui", self.update_platform_config_ui)
        self.platform.event_bus.subscribe("remove_your_agent", self.remove_agent)
        self.platform.event_bus.subscribe("append_your_agent", self.append_agent)
        self.platform.event_bus.subscribe("publish_commits", self.write_to_platform)
        self.platform.event_bus.subscribe("load_platform", self.load_platform)
        self.platform.event_bus.subscribe("platform_title_update", self.platform_title_update)
        
        # Name field initialization
        self.name_field = TextField(hint_text="Only letters, numbers, and underscores are allowed.", on_change=self.validate_fields)
        self.name_field.value = self.platform.title  # Set the value of the name field to the platform title
        self.name_field.on_change = lambda e: self.validate_text(self.name_field)
        
        # Address field initialization
        self.addresses_text_field = TextField(label="TCP Address", prefix_text="tcp://", on_change=self.validate_fields)
        self.address_field_pair = field_pair("Addresses", self.addresses_text_field)

        # Ports field initialization
        self.ports_field = TextField(value="22916", on_change=self.validate_fields)
        self.ports_field_pair = field_pair("Ports", self.ports_field)
        
        # Agent dropdown initialization
        self.agent_dropdown = numerate_agent_dropdown()
        self.agent_dropdown.on_change = self.validate_fields
        self.agent_dropdown_with_button = Row(
            controls=[
                Container(expand=3, content=self.agent_dropdown),
                Container(key='DO NOT HURT ME',
                          width=40,
                          content=IconButton(icon=icons.ADD_CIRCLE_OUTLINE_ROUNDED, on_click=self.add_agent, icon_color="white"))
            ]
        )

        # Columns of differing pages holding agents  
        self.platform_config_agent_column = Column(wrap=True, scroll=ScrollMode.AUTO)

        # Host field initialization
        self.host_field = numerate_host_dropdown()
        self.host_field_pair = field_pair("Host", self.host_field)
        
        self.bus_field_pair = field_pair("Bus Type", Text("Zmq", size=18, color="white"))

        # Grouping fields for display
        self.almost_fields = [
            self.host_field_pair,
            field_pair("Name", self.name_field),
            self.address_field_pair,
            self.ports_field_pair,
            self.bus_field_pair
        ]
        self.all_fields_formatted = divide_fields(self.almost_fields)

        self.comprehensive_view = Container(
            margin=margin.only(left=10, right=10, bottom=5, top=5),
            bgcolor="#20f4f4f4",
            border_radius=12,
            content=Column(
                scroll=ScrollMode.AUTO,
                alignment=MainAxisAlignment.START,
                spacing=10,  # Adjusted spacing for better separation
                controls=[
                    *self.all_fields_formatted,
                    Container(
                        height=70,
                        padding=padding.only(top=10, bottom=10, left=5, right=5),
                        content=Row(
                            expand=True,
                            controls=[
                                Container(expand=2, content=Text("Agents", size=20)),
                                Container(expand=3, content=self.agent_dropdown_with_button)
                            ]
                        )
                    ),
                    Container(
                        content=Row(
                            spacing=0,
                            controls=[
                                Container(expand=3, padding=padding.only(left=4), content=self.platform_config_agent_column),
                            ]
                        )
                    )
                ]
            )
        )


    def platform_title_update(self, data=None):
        self.name_field.value=self.platform.title
        attempt_to_update_control(self.name_field)

    def load_platform(self, data=None) -> None:
        """Subscribed to signal `load_platform`"""
        # print("Platform is loading")
        self.host_field.value = next(iter(self.platform.added_hosts))
        self.name_field.value = self.platform.title
        self.addresses_text_field.value = self.platform.address
        self.ports_field.value = self.platform.ports 
        attempt_to_update_control(self.platform.page)

    def forward_agent_removed(self, agent: LocalAgent) -> None:
        self.platform.event_bus.publish("agent_removed", agent)

    def remove_agent(self, agent: LocalAgent) -> None:
        """Subscribed to signal `remove_your_agent`"""
        key: str = agent.tile.key
        remove_from_selection(self.platform_config_agent_column, key)

    def forward_agent_appended(self, agent_name: str) -> None:
        self.platform.event_bus.publish("agent_appended", agent_name)

    def append_agent(self, agent: LocalAgent) -> None:
        """Subscribe to signal `append_your_agent`"""
        agent_tile = agent.clone_tile()
        self.platform_config_agent_column.controls.append(agent_tile)
        attempt_to_update_control(self.platform_config_agent_column)

    def write_to_platform(self, data=None) -> None:
        """Subscribed to signal `publish_commits`"""
        self.platform.title = self.name_field.value
        self.platform.address = self.addresses_text_field.value
        self.platform.ports = self.ports_field.value
        self.platform.added_hosts[self.host_field.value] = global_hosts[self.host_field.value]
        # print(self.platform.added_agents)
        # self.platform.publish("write_platform_to_file", None)
    
    def validate_fields(self, e) -> None:
        deploy: bool
        if (
            self.host_field.value and \
            self.addresses_text_field.value and \
            self.ports_field.value != "" and\
            self.validate_text(self.name_field) == True
        ):
            deploy = True
        else:
            deploy = False

        self.platform.event_bus.publish("toggle_deploy", deploy)

    def update_platform_config_ui(self, data=None):
        self.update_host_dropdown()
        self.update_agents_dropdown()
    
    def update_host_dropdown(self):
        new_host_field = numerate_host_dropdown()
        self.host_field_pair.content.controls[1].content = new_host_field  # Update the host field with new host values
        self.host_field = new_host_field
        attempt_to_update_control(self.host_field)

    def update_agents_dropdown(self):
        new_agent_dropdown = numerate_agent_dropdown()
        self.agent_dropdown_with_button.controls[0].content = new_agent_dropdown
        attempt_to_update_control(self.agent_dropdown_with_button)

    def validate_text(self, text_field: TextField) -> None:
        """
        Validate the text in `text_field`.

        Args:
            text_field (TextField): The text field to validate.
        """
        valid: bool
        valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
        input_text = text_field.value
        if all(c in valid_chars for c in input_text):
            text_field.error_text = None
            valid = True
        else:
            text_field.error_text = "Only letters, numbers, and underscores are allowed."
            valid = False
        text_field.update()
        return valid

    def add_agent(self, e) -> None:
        """
        Forward agent_name if not in added_agents
        """
        if self.agent_dropdown.value not in self.platform.added_agents.keys():
            # Tell platform_
            self.forward_agent_appended(self.agent_dropdown.value)



    def platform_config_view(self) -> Container:
        """
        Return the comprehensive view container for the platform configuration.

        Returns:
            Container: The comprehensive view container.
        """
        return self.comprehensive_view
