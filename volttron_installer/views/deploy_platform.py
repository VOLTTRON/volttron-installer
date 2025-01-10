# this page should allow you to potentially deploy multiple platforms
# i can clean up multiple stuff, i need to get the list of agents dynamically somehow ill talk to craig about that 
import flet as ft
from flet import *

from typing import Callable

import logging

_log = logging.getLogger(__name__)

class Agent:
    def __init__(self, agent_name, parent_container, agent_list):
        self.agent_name = agent_name
        self.parent_container = parent_container  # Reference to the parent container (column)
        self.agent_list = agent_list
        self.active = False  # Initial hover state

        self.label = Text(value=self.agent_name, color=self.get_agent_color())

        # Initialize container with default agent color
        self.agent_tile = Container(
            border_radius=10,
            padding=5,
            border=border.all(4, self.get_agent_color()),
            on_hover=self.color_hover_change,
            on_click=self.remove_self,
            content=self.label,
            
        )

    def get_agent_color(self):
        # Return color based on active state and initialize default colors
        return "red" if self.active else "green"

    def color_hover_change(self, e):
        # Update active state based on hover
        self.active = (e.data == "true")

        # Update the color based on the new hover state
        new_color = self.get_agent_color()
        self.agent_tile.border = border.all(4, new_color)
        self.label.color = new_color  # Update text color
        self.agent_tile.update()

    def remove_self(self, e):
        if self.agent_tile in self.parent_container.controls:
            # print("list of added agents in class:",self.agent_list)
            self.agent_list.remove(self.agent_name)
            # print("list of added agents in class:",self.agent_list)
            self.parent_container.controls.remove(self.agent_tile)
            self.parent_container.update()  # Update the UI to reflect changes

    def build_agent_card(self) -> Container:
        return self.agent_tile
 
#global total amount of agents variable
added_agents=[]

def deploy_platform_view(page: Page) -> View:
    from volttron_installer.views import InstallerViews as vi_views
    from volttron_installer.components.background import gradial_background
    from volttron_installer.modules.all_agents import agents
    
    # monolithic code; pressing button appends tile to main page


    #validate the name field
    def validate_text(e) -> None:
        valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
        input_text = e.control.value
        # Check if every character in the text is among the valid characters
        if all(c in valid_chars for c in input_text) and 0 <= len(input_text) <= 9:
            e.control.error_text = None  # Clear any previous error message
            submit_button.disabled = False
        else:
            error_messages = []
            if not all(c in valid_chars for c in input_text):
                error_messages.append("Only letters, numbers, and underscores are allowed.")
            e.control.error_text = " ".join(error_messages)
            submit_button.disabled = True
        submit_button.update()
        e.control.update()
    
    # Container containing the form title and form input pair
    def field_pair(text, input) -> Container:
        return  Container(
            height=70,
            padding=padding.only(top=10,bottom=10, left=5,right=5),
            content=Row(
                controls=[
                    Container(
                        expand=2,
                        content=Text(f"{text}",size=20)
                    ),
                    Container(
                        expand=3,
                        content=input
                    )
                ],
                spacing=0
            )
        )

    def divide_fields(field_list) -> list:
        div = Divider(height=9, thickness=3, color="white")
        #puts a divider in between each field pair in the field list 
        return [element for pair in zip(field_list, [div] * (len(field_list) - 1)) for element in pair] + [field_list[-1], div]
    

    def add_agent(e)-> None:
        if dd.value != None:
            if dd.value not in added_agents:
                agent_tile_to_add = Agent(dd.value, agent_column, added_agents).build_agent_tile()
                agent_column.controls.append(agent_tile_to_add)
                page.update()
                added_agents.append(dd.value)

    #func to restore the agents after swtiching pages
    def restore_agents():
        for agent_name in added_agents:
            agent_tile_to_add = Agent(agent_name, agent_column, added_agents).build_agent_tile()
            agent_column.controls.append(agent_tile_to_add)


    #name field
    name_field = TextField(
        hint_text="Only letters, numbers, and underscores are allowed.",
        on_change=validate_text
    )
    name_field_pair = field_pair("Name", name_field)

    #adress field
    all_addresses_checkbox = Checkbox(label="All Adresses")
    address_field = Container(content=all_addresses_checkbox)
    address_field_pair = field_pair("Adresses", address_field)

    #ports field
    ports_field = TextField()
    ports_field_pair = field_pair("Ports", ports_field)

    #bus field
    bus_field_pair = field_pair("Bus Type", Text("2mg", size= 18, color="white"))

    #all fields compiled and properlly managed
    all_field_pairs = [name_field_pair, address_field_pair, ports_field_pair, bus_field_pair]
    fields = divide_fields(all_field_pairs)
    
    #verify if the add platform form can be submitted whether or not the entire form fits the requirements    
    submit_button = OutlinedButton("Submit", disabled=True)

    #agent column where the added agents will be stored
    agent_column = Column()

    #dummy options for testing, will be replaced probably with a for loop iterating through all of the agents dynamically
    option1 = dropdown.Option(text="dummy1")
    option2 = dropdown.Option(text="dummy2")
    option3 = dropdown.Option(text="dummy3")
    dd = Dropdown(
        options=[
            option1, option2, option3
        ]
    )
    
    #puts the dropdown inside a row 
    dropdown_row_with_button = Row(
        controls=[
            Container(
                expand=3,
                content=dd
            ),
            Container(
                width=40,
                content=IconButton(icon=icons.ADD_CIRCLE_OUTLINE_ROUNDED, on_click=add_agent, icon_color="white"),
            )
        ]
    )

    the_awesome_background = gradial_background()

    #restore the agents after swtiching back to this page because i dont know how else to do it 
    restore_agents()
    return View(vi_views.deploy_platform.route, 
        [
            Stack(
                controls=[
                    the_awesome_background,
                    Column(
                        controls=[
                            Container( # header
                                #bgcolor="orange",
                                padding=padding.only(left=20,right=20),
                                content=Row(
                                    controls=[
                                        Text("Add Platform", size=60, color="white"),
                                        ElevatedButton(on_click= lambda _: page.go(vi_views.home.route)),
                                        #ElevatedButton(on_click=funny_func) # CHANGE IN PRODUCTION
                                    ],
                                    alignment=MainAxisAlignment.SPACE_BETWEEN
                                )
                            ),
                            #put into column
                            Container( # main transparent container to hold everything else
                                margin=margin.only(left=20,right=20, bottom=20),
                                bgcolor="#20f4f4f4",
                                expand=True,
                                border_radius=12,
                                content=Column( # parent column to house two other columns
                                    # how about we have a row return two columns, the left side can have containers with unifrom stying
                                    spacing=0,
                                    controls=[
                                        *fields,
                                        Container(
                                            expand=True,
                                            #bgcolor="blue",
                                            content=Column(
                                                spacing=0,
                                                controls=[
                                                    Container(
                                                        height=70,
                                                        padding=padding.only(top=10,bottom=10, left=5,right=5),
                                                        #bgcolor="red",
                                                        content=Row( # heading row will hold drop down and such
                                                            spacing=0,
                                                            controls=[
                                                                Container(
                                                                    #bgcolor="green",
                                                                    expand=2,
                                                                    content=Text("Agents", size=20)
                                                                ),
                                                                Container(
                                                                    #bgcolor="grey",
                                                                    expand=3,
                                                                    content=dropdown_row_with_button,
                                                                ),
                                                            ]
                                                        )
                                                    ),
                                                    Container(
                                                        expand=True,
                                                        content=Row(
                                                            spacing=0,
                                                            controls=[
                                                                Container(
                                                                    #bgcolor="purple",
                                                                    padding=padding.only(left=4),
                                                                    expand=2,
                                                                    content=agent_column
                                                                ),
                                                                #completetly empty container for formatting the agents column
                                                                # perhaps the save button will go on the  bottom right of this container
                                                                Container(
                                                                    expand=3,
                                                                    content=Stack(
                                                                        controls=[
                                                                            Container( # position submit button container 
                                                                                bottom=10,
                                                                                right=10,
                                                                                height=50,
                                                                                width=100,
                                                                                #padding=padding.only(left=20,right=20),
                                                                                #bgcolor="pink",
                                                                                content= submit_button
                                                                            )
                                                                        ]
                                                                    )
                                                                )
                                                            ]
                                                        ),
                                                    )
                                                ]
                                            )
                                        )
                                    ]
                                )
                            )
                        ],
                    ),
                ],
                expand=True
            )
        ],
    padding=0
    )