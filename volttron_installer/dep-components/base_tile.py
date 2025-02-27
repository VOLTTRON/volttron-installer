from volttron_installer.modules.create_field_methods import divide_fields, field_pair
from volttron_installer.components.default_tile_styles import build_default_tile
from volttron_installer.components.general_notifier import GeneralNotifier
from volttron_installer.modules.write_to_json import write_to_file, dump_to_var
from volttron_installer.modules.show_selected_tile import show_selected_tile
from volttron_installer.modules.global_event_bus import global_event_bus
from volttron_installer.modules.remove_from_controls import remove_from_selection
from volttron_installer.modules.attempt_to_update_control import attempt_to_update_control
from time import sleep
from flet import *
from dataclasses import fields
import asyncio
from volttron_installer.modules.styles import modal_styles2

class BaseTile:
    counter = dump_to_var("tile_id")

    def __init__(self, title: str):
        self.title = title
        if BaseTile.counter == {}:
            BaseTile.counter = 0
        BaseTile.counter += 1
        write_to_file("tile_id", BaseTile.counter)

    def build_tile(self) -> Container:
        tile = build_default_tile(self.title)
        tile.key = f"container: {self.counter}"
        return tile

    def list_attributes(self):
        """Returns a list of the child class' attributes"""
        attributes = []
        for attribute_name in self.__dict__:
            attributes.append(attribute_name)
        return attributes


class BaseForm:
    def __init__(self, page: Page, form_fields: dict):
        self.page = page
        self.form_fields = form_fields
        self.val_constructor = []
        self.non_fields = []
        self.additional_content = [] # for anything special

        self.general_notifier = GeneralNotifier(page=self.page)

        self.overwrite: bool = False

        for key, field in self.form_fields.items():
            if isinstance(field, TextField):
                self.val_constructor.append(field)
            else:
                self.classify_field(field)

        self.revert_button = IconButton(icon=icons.UNDO, tooltip="Undo changes", visible=False)
        self.changes_indicator: Stack[Container] = Stack(
                                        [
                                            Container(
                                                # bgcolor="purple",
                                                content=Container(width=20, height=20),
                                                alignment=alignment.center
                                            ),
                                            Container(
                                                content=Container(
                                                    width=20,
                                                    height=20,
                                                    bgcolor=colors.with_opacity(1, "orange"),
                                                    border_radius=50,
                                                    animate=animation.Animation(2000, AnimationCurve.EASE_IN)
                                                    ),
                                                alignment=alignment.center,
                                            ),
                                        ],
                                        visible=False,
                                        width=50,
                                        height=50,
                                    )

        self.changed = False
        self.is_detecting_changes = False
        # Initialize other necessary variables or UI components

        self.submit_button = OutlinedButton(text="Save", disabled= not self.changed, on_click=self.save_config)
        self.formatted_fields: any = self.create_fields()
        self._form = Column(
            scroll=ScrollMode.AUTO,
            expand=3,
            controls=[
                *self.formatted_fields,
                Row(
                    [
                        Container(content=self.submit_button, margin=margin.only(left=10)),
                        self.revert_button,
                        self.changes_indicator
                    ]
                ),
                *self.additional_content
            ]
        )

    def changes_finalized(self, message: str | int = False):
        """Once we either revert or save our changes,
         we should disable the indicator and revert button """
        self.revert_button.visible = False
        self.changes_indicator.visible = False
        self.changed = False
        self.is_detecting_changes = False  # Reset the flag when changes are finalized

        # Update all UI components
        attempt_to_update_control(self.revert_button)
        attempt_to_update_control(self.changes_indicator)
        self.toggle_submit_button(self.changed)
        attempt_to_update_control(self.page)

        if message:
            self.general_notifier.display_snack_bar(message=message)

    def revert_changes(self, revert_map: dict) -> None:
        """Method to revert changes made to the form.
        Args:
            revert_map: A dictionary containing a Flet TextField and the previous saved data to
                        revert to as a kwarg
        """
        textfields: list[TextField] = revert_map.keys()

        print(revert_map)

        for i in textfields:
            i.value = revert_map[i]
            attempt_to_update_control(i)
        self.toggle_submit_button(self.changed)
        self.changes_finalized(2)

    def changes_detected(self) -> None:
        if self.is_detecting_changes:
            return  # Exit if the function is already running
        self.is_detecting_changes = True  # Set the flag to indicate the function is running
        print("changes are #detected \n")
        self.changed = True
        self.revert_button.visible=True
        self.changes_indicator.visible=True
        self.page.update()

        ring_one: Container = self.changes_indicator.controls[1].content
        while self.changed:
            if ring_one.height == 20:
                ring_one.animate = animation.Animation(1500, AnimationCurve.EASE_IN)
                ring_one.height = 24
                ring_one.width = 24
                ring_one.bgcolor=colors.with_opacity(0.45, "orange")
                self.page.update()
                sleep(2.5)


            elif ring_one.height == 24:
                ring_one.animate = animation.Animation(1500, AnimationCurve.EASE_IN)
                ring_one.height = 20
                ring_one.width = 20
                ring_one.bgcolor=colors.with_opacity(.9, "orange")

                self.page.update()
                sleep(2.5)

            elif self.changed == False:
                print("we broke bro")
                break

    def classify_field(self, field):
        if hasattr(field, "key"):
            if field.key == "pass":
                self.additional_content.append(field)
            else:
                self.non_fields.append(field)
        else:
            self.non_fields.append(field)

    def refresh_form(self, instance: object) -> None:
        """Post init, will refresh form values"""
        instance_fields = fields(instance)
        instance_values = [getattr(instance, field_object.name) for field_object in instance_fields]
        for i, attribute in zip(self.val_constructor, instance_values):
            if isinstance(i, TextField):
                i.value = attribute
        self.page.update()

    def create_fields(self) -> list:
        """Pairs fields up with title then returns divided up field pairs."""
        field_pairs = []
        try:
            for obj, key in zip(self.val_constructor, self.form_fields.keys()):
                if obj == self.form_fields[key]:
                    field_pairs.append(field_pair(key, self.form_fields[key]))

            for i in list(self.form_fields.keys()):
                if self.form_fields[i] in self.non_fields:
                    field_pairs.append(field_pair(i, self.form_fields[i]))
            return divide_fields(field_pairs)
        except:
            # # print("form_fields contains unhashable kwargs")
            return None

    def validate_fields(self, e) -> None:
        # Implement field validation logic and toggle submit button state.
        valid: bool = all(field.value for field in self.val_constructor)
        self.toggle_submit_button(valid)
        if not self.is_detecting_changes:
            self.changes_detected()

    async def save_config(self, e) -> None:
        # This method will be overwritten
        pass

    def toggle_submit_button(self, state: bool) -> None:
        self.submit_button.disabled = not state
        attempt_to_update_control(self.submit_button)

    def write_to_file(self, file: str, global_lst: list):
        write_to_file(file, global_lst)

    def replace_key(self, dictionary: dict, old_key: str, new_key: str):
        if old_key in dictionary:
            dictionary[new_key] = dictionary.pop(old_key)

    async def detect_conflict(self, working_dict: dict, new_name: str, old_name: str) -> bool | str:
        print("\nDetecting if there is a conflict")

        if new_name == old_name:
            print("We are just saving without changing the name.")
            return "rename"  # No conflict since it's the same name

        print(f"Here is our working dict:\n{working_dict}\nHere is the new name we are trying to parse:\n{new_name}")

        if new_name in working_dict:
            print('Conflict detected')
            overwrite_decision = await self.warning_modal(new_name)
            return overwrite_decision  # True if we want to overwrite, False otherwise
        else:
            return "clean"  # No conflict, as the new name does not exist


    async def warning_modal(self, new_name: str) -> bool:
        loop = asyncio.get_event_loop()

        def no_overwrite(e):
            self.page.close(modal)
            self.overwrite = False
            loop.call_soon_threadsafe(future.set_result, False)

        def enable_overwrite(e):
            self.page.close(modal)
            self.overwrite = True
            loop.call_soon_threadsafe(future.set_result, True)

        modal_content = Column(
            alignment= alignment.center,
            controls=[
                Text("WARNING!", color="red", size=22),
                Text(f"You're about to overwrite a configuration named: ", spans=[
                    TextSpan(f"{new_name}", TextStyle(decoration=TextDecoration.UNDERLINE,font_family="Consolas"))
                ], size=18),
                Row(
                    alignment=MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        OutlinedButton(content=Text("Cancel", color="red"), on_click=no_overwrite),
                        OutlinedButton(text="Overwrite", on_click=enable_overwrite)
                    ]
                )
            ]
        )

        modal = AlertDialog(
            modal=False,
            bgcolor="#00000000",
            content=Container(
                **modal_styles2(),
                width=400,
                height=170,
                content=modal_content
            )
        )

        # Create a future for the result
        future = loop.create_future()
        self.page.open(modal)
        await future
        return self.overwrite

    async def check_overwrite(self, old_name: str, working_dict: dict, new_name: str) -> bool | str:
        print(f"\nChecking the overwrite of '{old_name}' with '{new_name}'")

        if old_name == new_name:
            print("We are renaming the existing item without changing its name.")
            return "rename"

        conflict_detected = await self.detect_conflict(working_dict, new_name, old_name)

        return conflict_detected


    def build_form(self) -> Column:
        return self._form

class BaseTab:
    def __init__(self, instance_tile_column: Column, page: Page):
        self.page = page

        # Get our column that holds our tiles and enable scroll on it
        self.instance_tile_column = instance_tile_column
        self.instance_tile_column.scroll = ScrollMode.AUTO

        # Initialize column widths
        self.left_column_width = 200  # Initial width for the instance tile column
        self.right_column_width = page.width - self.left_column_width - 10  # Initial width for the form column

        # Get our tab so the children can access a consistent variable without having to run the function again
        self.tab = self.build_base_tab()

        # Init general notifier
        self.general_notifier = GeneralNotifier(self.page)
        global_event_bus.subscribe("soft_remove", self.soft_remove)

    def build_base_tab(self):
        # Initialize form container
        form_container = Container(width=self.right_column_width, content=ListView(controls=[Column(expand=3)], expand=3))

        def pan_update(e):
            # Perform the panning logic to adjust column widths
            self.left_column_width = max(200, self.left_column_width + e.delta_x)  # Set a minimum width of 50
            self.right_column_width = max(300, self.page.width - self.left_column_width - 10)  # Adjust the width of the right column

            # Update the dimensions of the container elements
            self.instance_tile_column.width = self.left_column_width
            form_container.width = self.right_column_width

            # Refresh the UI
            # self.instance_tile_column.update()
            # form_container.update()
            tab_view.update()
            self.page.update()

        vertical_divider = GestureDetector(
            mouse_cursor=MouseCursor.RESIZE_COLUMN,
            content=VerticalDivider(
                width=3,
                thickness=3,
                color="white"
            ),
            on_pan_update=pan_update
        )

        tab_view = Container(
            height=900,
            padding=padding.only(left=10),
            margin=margin.only(left=10, right=10, bottom=5, top=5),
            bgcolor="#20f4f4f4",
            border_radius=12,
            content=Row(
                spacing=0,
                controls=[
                    ListView(controls=[Container(content=self.instance_tile_column, padding=padding.only(top=7))], expand=2),
                    vertical_divider,
                    form_container
                ],
                expand=True
            )
        )
        return tab_view

    def refresh_tiles(self, file_name: str, global_dict: dict, instance_cls: type, instance_form_cls: type):
        if not self.contains_container():  # Checking if the container exists
            for key, item in global_dict.items():
                instance_cls_fields = fields(instance_cls)
                instance_cls_attributes = [attribute.name for attribute in instance_cls_fields if attribute.init]  # Only include attributes marked with init=True

                # Ensure the first attribute in 'instance_cls_attributes' gets the key's value
                instance_constructor = {attr: item.get(attr) for attr in instance_cls_attributes}
                if instance_cls_attributes:  # Ensure there is at least one attribute
                    first_attr = instance_cls_attributes[0]
                    instance_constructor[first_attr] = key

                # Create the instance with the constructor
                instance = instance_cls(**instance_constructor)

                # Extract instance_tile from the new instance
                instance_values = [getattr(instance, field.name) for field in instance_cls_fields]
                instance_tile: Container = instance_values[-1]

                # Create the form with the new instance
                form: BaseForm = instance_form_cls(instance, self.page)

                # Configure the new instance
                self.configure_new_instance(file_name, global_dict, instance_values, instance_tile, form, instance)

    def add_new_tile(self, global_list, file_name: str, object: BaseTile, form: BaseForm):
        field_objects = fields(object)
        attributes = [field_object.name for field_object in field_objects]
        object_constructor = {}
        for i, attribute in enumerate(attributes[:-1]):
            if i == 0:
                object_constructor[attribute] = "Configure Me!"
            else:
                object_constructor[attribute] = ""
        new_instance: BaseTile = object(**object_constructor)
        new_form = form(new_instance, self.page)

        new_instance_fields = fields(new_instance)
        new_instance_values = [getattr(new_instance, field_object.name) for field_object in new_instance_fields]
        new_tile: Container = new_instance_values[-1]

        self.configure_new_instance(file_name, global_list, new_instance_values, new_tile, new_form, new_instance)

    def configure_new_instance(self, file_name: str, global_list: list, instance_values, tile: Container, form: BaseForm, instance):
        tile.on_click = lambda e: self.select_tile(e, form)
        tile.content.controls[1].on_click = lambda e: self.remove_warning_wrapper(e, global_list, file_name,
                                                                                   instance_attributes={"name": instance_values[0], "id": tile.key})
        self.instance_tile_column.controls.append(tile)
        attempt_to_update_control(self.instance_tile_column)
        form.refresh_form(instance)

    def contains_container(self):
        """Just checks if there is a container in the instance_tile_column"""
        for control in self.instance_tile_column.controls:
            if isinstance(control, Container):
                return True
        return False

    def soft_remove(self, key: str) -> None:
        remove_from_selection(self.instance_tile_column, key)
        self.tab.content.controls[2].content.controls[0] = Column(expand=3)
        self.page.update()

    async def remove_self(self, global_lst: dict, file_name: str, instance_attributes: dict):
        if instance_attributes["name"] in global_lst.keys():
            del global_lst[instance_attributes["name"]]
        write_to_file(file_name, global_lst)
        remove_from_selection(self.instance_tile_column, instance_attributes["id"])
        self.tab.content.controls[2].content.controls[0] = Column(expand=3)
        self.page.update()
        global_event_bus.publish("update_global_ui", None)
        self.general_notifier.display_snack_bar("Removed successfully!")

    async def remove_warning(self, global_lst: dict, file_name: str, instance_attributes: dict) -> None:
        loop = asyncio.get_event_loop()
        subject_name = instance_attributes["name"]

        def remove_failed(e):
            self.page.close(modal)
            loop.call_soon_threadsafe(future.set_result, False)

        def remove_continued(e):
            self.page.close(modal)
            loop.call_soon_threadsafe(future.set_result, True)

        modal_contents = Column(
            controls=[
                Text("WARNING!", color="red", size=22),
                Text(f"Are you sure you want to permanently remove ", spans=[
                    TextSpan(
                        f"{subject_name}",
                        TextStyle(
                            font_family="Consolas",
                            bgcolor=colors.with_opacity(0.2, "black")
                            ))
                        ]
                        ,size=18
                    ),
                Row(
                    alignment=MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        OutlinedButton(content=Text("Cancel", color="red"), on_click=remove_failed),
                        OutlinedButton(text="Continue", on_click=remove_continued),
                    ]
                )
            ]
        )

        modal = AlertDialog(
            modal=False,
            bgcolor="#00000000",
            content=Container(
                **modal_styles2(),
                width=400,
                height=170,
                content=modal_contents
            )
        )

        future = loop.create_future()
        self.page.open(modal)
        result = await future
        if result:
            await self.remove_self(global_lst, file_name, instance_attributes)

    def select_tile(self, e, instance_form: BaseForm) -> None:
        self.show_selected_form(e, instance_form)
        show_selected_tile(e, self.instance_tile_column)
        self.page.update()

    def show_selected_form(self, e, instance_form: BaseForm) -> None:
        self.tab.content.controls[2].content.controls[0] = instance_form.build_form()
        attempt_to_update_control(self.tab)

    def remove_warning_wrapper(self, e, global_list, file_name, instance_attributes):
        asyncio.run(self.remove_warning(global_list, file_name, instance_attributes))
