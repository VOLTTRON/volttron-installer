from email.errors import CloseBoundaryNotFoundDefect
from volttron_installer.components.base_tile import BaseForm, BaseTab, BaseTile
from flet import *
from volttron_installer.modules.global_configs import global_drivers, find_dict_index
from volttron_installer.modules.validate_field import  check_json_field
from volttron_installer.modules.global_event_bus import global_event_bus
from volttron_installer.modules.prettify_json import prettify_json
from volttron_installer.modules.conversion_methods import json_string_to_csv_string, csv_string_to_json_string, identify_string_format
from volttron_installer.modules.attempt_to_update_control import attempt_to_update_control
from dataclasses import dataclass, field
from volttron_installer.modules.styles import data_table_styles
import csv
import io
import json

# PLAN: MAKE CONTENT FIELD BE PARCED AND FORM THE DATATABLE BASED OFF OF IT AND HAVE ERROR HANDLING IF IMPROPER
# CONTENT WAS PASTED IN
# REWRITE DATATABLE STRUCTURE
# CREATE FUNCTION THAT UPDATES BOTH FIELDS, THAT FORMATS THE JSON FIELD ASWELL BUT IGNORES THE SPACES TEEHEE

# GO TO THIRD TO FIRST AND SCROLL UP FOR OLD COLUMN AND ROW CODE 

# Constants
key_constructor = [
    "name",
    "content",
    "type",
]

@dataclass
class Config(BaseTile):
    name: str
    content: str
    type: str  # CSV or JSON

    tile: Container = field(init=False)

    def __post_init__(self):
        super().__init__(self.name)  # Initialize BaseTile with name
        self.tile = self.build_config_tile()

    def build_config_tile(self) -> Container:
        return self.build_tile()  # Calls BaseTile's build_tile method

class ConfigForm(BaseForm):
    def __init__(self, config, page: Page):
        self.config: Config = config # initialized Config
        self.page = page

        self.name_field = TextField(on_change=self.validate_fields)
        self.view_type_radio_group = RadioGroup(
            disabled=False,
            value=self.config.type,
            on_change=self.type_change,
            content=Row(
                spacing=25,
                controls=[
                    Radio(label="JSON", value="JSON"),
                    Radio(label="CSV", value="CSV")
                ]
            )
        )

        self.content_field = TextField(label="Paste or type your configuration", multiline=True, on_change=self.content_field_change)
        self.json_content_editor = TextField(
                                multiline=True,
                                autofocus=True,
                                height=800,
                                border=InputBorder.UNDERLINE,
                                filled=True,
                                fill_color=colors.with_opacity(0.5, colors.BLUE_GREY_300),
                                expand=True,
                                on_change=self.validate_fields,
                            )
        self.content_input_container: Container = Container(content=Text("Please select the type of content")) # blank container that will have its content plugged in and out depending on type of input field
        
        self.content_container: Container = Container(
            key="pass",
            bgcolor=colors.with_opacity(0.6, "black"),  # delete later, for formatting reasons
            margin=margin.only(top=15, left=15, right=15),
            expand=True,
            content=Column(
                scroll=ScrollMode.AUTO,
                controls=[
                    Row(
                        scroll=ScrollMode.AUTO,
                        controls=[
                            self.content_input_container  # Will take up the available space due to parent expand properties
                        ]
                    )
                ]
            )
        )

        data_table_columns = [self.craft_data_column() for i in range(13)]
        data_table_rows =[self.craft_data_row(13) for i in range(20)]

        self.csv_data_table = DataTable(
                                **data_table_styles(),
                                column_spacing=0,
                                horizontal_margin=0,
                                columns=data_table_columns,
                                #[
                                    # DataColumn(
                                    #     label=Container(content=Text("Empty Column", color="black", weight="bold")),
                                    # )
                                #],
                                rows=data_table_rows,
                                # [
                                #     DataRow(
                                #         cells=[
                                #             DataCell(content=Text("Empty Cell"))
                                #         ]
                                #     )
                                # ]
                            )
        
        form_fields = {
            "Name": self.name_field,
            "View": self.view_type_radio_group,
            "Content" : Container(content=self.content_field),
            "content container" : self.content_container,
        }

        super().__init__(page, form_fields)
        self.config_mode: str | None = self.config.type if isinstance(self.config.type, str) else None
        self.content_field_validity: bool[False] = False
        self.submit: bool = False
        self.content_value: str = self.config.content if isinstance(self.config.content, str) else ""
        self.detected_content_format: str = self.config.type
        self.csv_data : str
        self.json_data : str
        self.__post_init__()

    def __post_init__(self) -> None:
        self.update_detected_content_format()
        attempt_to_update_control(self.content_field)
        if self.config_mode == "JSON":
            self.json_content_editor.value = prettify_json(self.json_content_editor.value)
        else:
            self.load_csv_to_data_table(self.content_value)
        self.plug_into_content_input_container()

    def update_detected_content_format(self)-> None:
        self.detected_content_format: str = identify_string_format(self.content_value)

    def content_field_change(self, e) -> None:
        # Set the new content value
        self.content_value = e.control.value
        self.update_fields(None)

    def load_csv_to_data_table(self, csv_string: str =None) -> None:
        input_data = csv_string
        input_io = io.StringIO(input_data)
        reader = csv.reader(input_io)

        csv_data = list(reader)
        input_io.close()
        
        column_headers = csv_data[0] if csv_data else []
        num_of_columns = len(csv_data[0]) if csv_data else 0

        csv_data = csv_data[1:]

        # if num_of_columns > 3:
        #     len_difference: int = num_of_columns - len(self.csv_content_field.columns)
        #     self.add_new_data_column(None, len_difference)

        for data_column, header in zip(self.csv_data_table.columns, column_headers):
            data_column.label.content.value = header

        # if len(csv_data) > 3:
        #     len_difference: int = len(csv_data) - len(self.csv_data_table.rows)
        #     for i in range(len_difference):
        #         self.add_new_data_row(None)

        for data_row, content in zip(self.csv_data_table.rows, csv_data):
            for cell, value in zip(data_row.cells, content):
                cell.content.content.value = value

        attempt_to_update_control(self.csv_data_table)
                
    def data_table_to_csv(self) -> str:
        output = io.StringIO()
        csv_writer = csv.writer(output)

        # Write the header row
        header_row = []
        for col in self.csv_data_table.columns:
            header_content_container = col.label
            if isinstance(header_content_container, Container) and isinstance(header_content_container.content, TextField):
                header_value = header_content_container.content.value
                if header_value and header_value.strip() and ',' not in header_value:
                    header_row.append(header_value)
            else:
                continue  # Skip the column if it's not a TextField inside a Container

        # Ensure we only write the row if it is not empty
        if header_row:
            csv_writer.writerow(header_row)

        # Write the data rows
        for row in self.csv_data_table.rows:
            csv_row = []
            for cell, _ in zip(row.cells, range(len(header_row))):
                txt_field = cell.content.content
                if isinstance(txt_field, TextField):
                    cell_value = txt_field.value
                    if cell_value and cell_value.strip() and ',' not in cell_value:
                        csv_row.append(cell_value)
                    else:
                        csv_row.append("")  # Append an empty string for invalid values
                else:
                    csv_row.append("")  # Append an empty string if it's not a TextField inside Container

            # Remove trailing empty values
            while csv_row and not csv_row[-1]:
                csv_row.pop()

            # Avoid writing a row if it has no valid data
            if csv_row:
                csv_writer.writerow(csv_row)
        print("this is what im outputting as data_table to csv: ", output.getvalue)
        return output.getvalue()

    def craft_data_column(self)-> DataColumn:
        return DataColumn(
                    label=Container(
                        padding=padding.only(left=10),
                        height=50,
                        width=85,
                        content=TextField(border="none")
                    )
                )
    
    def craft_data_row(self, columns: int)-> DataRow:
        cell_list=[self.craft_data_cell() for i in range(columns)]
        return DataRow(cells=cell_list)
    
    def craft_data_cell(self)-> DataCell:
        return DataCell(
            content=Container(
                padding=padding.only(left=10),
                height=50,
                width=85,
                content=TextField(border="none")
            ),
        )

    def update_fields(self, e) -> None:
        self.update_detected_content_format()
        if self.detected_content_format == "CSV":
            self.json_content_editor.value = csv_string_to_json_string(self.content_value)
            self.load_csv_to_data_table(self.content_value)
        elif self.detected_content_format == "JSON":
            self.json_content_editor.value = prettify_json(self.content_value)
            self.load_csv_to_data_table(json_string_to_csv_string(self.content_value))
        attempt_to_update_control(self.content_field)
        attempt_to_update_control(self.json_content_editor)

        self.validate_fields(None)


    def attempt_to_update_control(self, control: Control)->None:
        if control.page:
            try:
                control.update()
            except Exception as ex:
                print("Unexpected error updating control at memory address: {control}", ex)

    def plug_into_content_input_container(self):
        if self.config_mode == "JSON":
            self.content_input_container.content = self.json_content_editor
        elif self.config_mode =="CSV":
            self.content_input_container.content = Container(expand=True, content=self.csv_data_table)
        attempt_to_update_control(self.content_input_container)


    def clean_json_string(self, json_string: str) -> dict:
        parced_string = json_string.replace("\r", "").replace("\\", "").replace("\n" , "").replace(" ", "")
        try:
            decoded_string = json.loads(parced_string)
            cleaned_string = json.dumps(decoded_string)
            return cleaned_string
        except:
            return parced_string

    def validate_fields(self, e) -> None:
        fields = [self.form_fields[i].value for i in self.form_fields.keys() if hasattr(self.form_fields[i], 'value')]
        all_fields_valid = all(fields)

        content_valid = self.correct_input() is not False

        if all_fields_valid and content_valid and self.submit:
            self.toggle_submit_button(True)  # Enable button if all fields are valid
        else:
            self.toggle_submit_button(False)  # Disable button if any field is not valid

    def correct_input(self) -> bool:
        if self.config_mode == "CSV":
            return True
        elif self.config_mode == "JSON":
            if self.json_content_editor.page:  # Ensure json_content_field is in page
                return check_json_field(self.json_content_editor)
            else:
                return False

    def type_change(self, e):
        # This means if our OLD type was JSON
        if self.config_mode == "JSON":
           self.content_value = self.clean_json_string(self.json_content_editor.value)
        # Was our OLD type CSV?
        elif self.config_mode == "CSV":
            self.content_value = self.data_table_to_csv()
        
        self.content_field.value = self.content_value
        attempt_to_update_control(self.content_field)

        self.config_mode = e.control.value
        self.submit = True
        self.plug_into_content_input_container()

        self.update_fields(None)
        self.validate_fields(e)

    def save_config(self, e) -> None:
        # Update the config object with current values from the fields
        self.config.type = self.view_type_radio_group.value
        
        content_data=self.content_value
        if self.config_mode == "JSON":
            content_data = self.clean_json_string(self.json_content_editor.value)

        elif self.config_mode == "CSV":
            content_data=self.data_table_to_csv()

        self.config.content = content_data

        old_config_name = self.config.name
        self.config.name = self.name_field.value
        index = find_dict_index(global_drivers, old_config_name)

        config_dictionary_appendable = {
            "name": self.config.name,
            "type": self.config.type,
            "content": self.config.content,
        }

        # If an existing entry already exists
        if index is not None:
            # Update the existing entry
            global_drivers[index] = config_dictionary_appendable
        else:
            # Add a new entry
            global_drivers.append(config_dictionary_appendable)

        # Update the UI tile content
        self.config.tile.content.controls[0].value = self.config.name
        self.page.update()
        
        # Write the changes to file
        self.write_to_file("drivers", global_drivers)


class ConfigStoreManagerTab(BaseTab):
    def __init__(self, page: Page) -> None:
        self.list_of_configs = Column(
            expand=2,
            controls=[
                OutlinedButton(text="Setup a Config", on_click=self.add_new_config)
            ]
        )

        super().__init__(self.list_of_configs, page)
        self.page = page
        global_event_bus.subscribe("tab_change", self.tab_change)

    def add_new_config(self, e) -> None:
        self.add_new_tile(global_drivers, "drivers", Config, ConfigForm)

    def tab_change(self, selected_tab):
        self.refresh_tiles("drivers", global_drivers, Config, ConfigForm)

    def build_config_store_tab(self) -> Container:
        return self.tab
