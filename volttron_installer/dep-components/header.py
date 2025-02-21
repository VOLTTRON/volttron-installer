import pprint
from volttron_installer.modules.attempt_to_update_control import attempt_to_update_control
from volttron_installer.modules.validate_field import validate_text
from volttron_installer.components.platform_components.platform import Platform
from volttron_installer.modules.global_configs import platforms
from flet import *
import asyncio

from volttron_installer.modules.write_to_json import write_to_file

class Header:
    """
    Class to represent and manage the header section of the platform management application.

    Attributes:
        shared_instance (Platform): Shared instance of the Platform class containing platform information and methods.
        route (str): The route to go back to on clicking the back button.
    """
    def __init__(self, shared_instance: Platform, route: str):
        """
        Initialize a Header instance.

        Args:
            shared_instance (Platform): Shared instance of the Platform class.
            route (str): Route to go back to on clicking the back button. (Will probably
                         forever be `/` but its future proofed at least!!)
        """
        self.platform: Platform = shared_instance
        self.route_back_to: str = route
        self.edit_mode: bool = False

        self.deploy_button = OutlinedButton(text="Deploy", disabled=True, on_click=self.deploy_platform)

        # Subscribe to platform events
        self.platform.event_bus
        self.platform.event_bus.subscribe("toggle_deploy", self.adjust_submit_validity)
        self.platform.event_bus.subscribe("update_global_ui", self.update_header_ui)

        # Initialize editing logic for button icons
        self.editing_icon = icons.EDIT

        self.delete_program_button = IconButton(icon=icons.DELETE, on_click=self.remove_platform, tooltip="Remove Platform")
        self.edit_program_title_button = IconButton(icon=self.editing_icon, on_click=self.handle_editing_mode)
        self.edit_delete_grouped = Container(content=Row(controls=[self.edit_program_title_button, self.delete_program_button]))

        # Additional Header components
        self.deployed_indicator = Row(
            [
                Container(**self.indicator_styles(self.platform.deployed)),
                TextButton(text=f"{self.get_state()}")
            ],
            spacing=0
        )
        self.running_indicator = Row(
            [
                Container(**self.indicator_styles(self.platform.running)),
                TextButton(text=f"{self.get_status()}")
            ],
            spacing=0
        )

        # Logic for the title editing functionality
        self.title_container = Container(visible=not self.edit_mode, content=Text(value=f"{self.platform.title}", size=24))
        self.title_editing_field = TextField(
            value=self.platform.title, 
            visible=self.edit_mode,
            width=100, 
            on_change=lambda e: validate_text(self.title_editing_field, self.edit_program_title_button)
        )
        self.title_edit_container = Row(controls=[self.title_container, self.title_editing_field], wrap=True)

        self.header = Container(
            padding=padding.only(left=20, right=20, top=20),
            content=Row(
                spacing=18,
                wrap=True,
                controls=[
                    Row(
                        controls=[
                            IconButton(
                                icon=icons.ARROW_BACK_IOS_NEW,
                                tooltip="Exit Platform",
                                icon_color="white",
                                icon_size=25,
                                on_click=lambda e: self.platform.page.go(self.route_back_to)
                            ),
                            self.title_edit_container
                        ]
                    ),
                    Container(
                        content=Row(
                            controls=[
                                self.edit_delete_grouped, 
                                self.deploy_button, 
                                self.running_indicator, 
                                self.deployed_indicator
                            ]
                        )
                    )
                ],
                alignment=MainAxisAlignment.SPACE_BETWEEN,
            ),
        )
    
    # NOTE;
    # Ripped completely from platform_tile.py
    def get_status(self) -> str:
        status = "ON" if self.platform.running == True else "OFF"
        if status == "ON":
            # Method to update platform tile UI
            pass 
        return status

    def get_state(self) -> str:
        return "Un-deployed" if self.platform.deployed == False else "Deployed"

    def indicator_styles(self, bool) -> dict:
        return {
            "width":15,
            "height": 15,
            "border_radius": 15,
            "bgcolor": "green" if bool else colors.with_opacity(.45, "red")
        }

    def adjust_submit_validity(self, state: bool):
        self.deploy_button.disabled = not state
        attempt_to_update_control(self.deploy_button)

    def deploy_platform(self, e) -> None:
        self.platform.event_bus.publish("deploy_platform", None)
        self.platform.event_bus.publish('update_ui', None)
        self.adjust_submit_validity(False)

    async def remove_platform(self, e) -> None:
        from volttron_installer.components.confirmation_modal import ConfirmationModal

        modal_result = await ConfirmationModal(self.platform.page).execute_confirmation("WARNING", ["Are you sure you want to permanently delete this platform?"])
        if modal_result:

            # 2 step process,
            #   1: send out the platform.tile key to the home to be removed.
            #   2: try to take it out of json by the unique url. catch the non index error if it isn't even in json
            # NOTE:
            # This try except block is muting an error. when we publish the `remove_platform` signal, the home tab
            # calls a function to remove the platform tile from the page and tries to update the page, thats when
            # we get our "cannot update control thats not in the page" error.
            try:
                self.platform.page.go("/")
                self.platform.snack_bar.display_snack_bar("Removed Platform!")
                self.platform.global_bus.publish("remove_platform", self.platform.tile_key)
            except:
                print("meoww")

            try: 
                del platforms[self.platform.generated_url]
                write_to_file("platforms", platforms)
            except:
                print("Platform has not been saved to json! smoothly removed")

    def update_header_ui(self, data = None) ->None:
        self.title_container.content.value = self.platform.title
        attempt_to_update_control(self.title_container)

        # Updating the running indicator if need be
        self.running_indicator.controls[0] = Container(**self.indicator_styles(self.platform.deployed))
        self.running_indicator.controls[1].text = f"{self.get_state()}"

        # Updating the deployed indicator if need be
        self.deployed_indicator.controls[0] = Container(**self.indicator_styles(self.platform.deployed))
        self.deployed_indicator.controls[1].text = f"{self.get_status()}"

        attempt_to_update_control(self.platform.page)

    def handle_editing_mode(self, e) -> None:
        if self.edit_mode:
            self.platform.title = self.title_editing_field.value
            self.title_container.content.value = self.platform.title  # Update the text value
            self.platform.event_bus.publish("platform_title_update")
            

        self.edit_mode = not self.edit_mode
        self.title_container.visible = not self.edit_mode
        self.title_editing_field.visible = self.edit_mode

        # Update the editing icon
        self.edit_program_title_button.icon = icons.SAVE if self.edit_mode else icons.EDIT
        self.platform.page.update()

    def return_header(self) -> Container:
        return self.header
