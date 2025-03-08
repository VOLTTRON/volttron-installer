import typing
import reflex as rx
from ..buttons import add_icon_button, icon_button_wrapper
from ..form_components import form_entry
import asyncio

# class CSVDataField(rx.ComponentState):
#     _selected_variant: str = "Default 1"  # Internal state
#     num_rows: int = 10
#     _row_iter: list[int] = list(range(num_rows))
    
#     variants: dict[str, dict[str, list[str]]] = {
#         "Default 1" : {
#             "Reference Point Name": ["default 1"]*num_rows,
#             "Volttron Point Name": [""]*num_rows,
#             "Units": [""]*num_rows,
#             "Units Details": [""]*num_rows,
#             "Modbus Register": [""]*num_rows,
#             "Writable": [""]*num_rows,
#             "Point Address": [""]*num_rows,
#             "Default Value": [""]*num_rows,
#             "Notes": [""]*num_rows,
#         },
#         "Default 2": {
#             "Point Name": [""]*num_rows,
#             "Volttron Point Name": [""]*num_rows,
#             "Units": [""]*num_rows,
#             "Unit Details": [""]*num_rows,
#             "BACnet Object Type": [""]*num_rows,
#             "Property": [""]*num_rows,
#             "Writable": ["f"]*num_rows,
#             "Index": [""]*num_rows,
#             "Notes" : [""]*num_rows,
#         }
#     }

#     selected_cell: str = ""

#     # Reactive vars
#     @rx.var(cache=True)
#     def working_dict_headers(self) -> list[str]: return list(self.variants[self.selected_variant].keys())

#     @rx.var(cache=True)
#     def variant_selections(self) -> list[str]: return list(self.variants.keys())

#     @rx.var(cache=True)
#     def working_dict_rows(self) -> list[list[str]]:
#         # Accessing our dict values horizontally:
#         working_dict = self.variants[self.selected_variant]
#         headers = list(working_dict.keys())
        
#         num_rows = len(list(working_dict.values())[0])
#         rows = []
        
#         for i in range(num_rows):
#             row = [working_dict[header][i] for header in headers]
#             rows.append(row)
            
#         return rows

#     @rx.var(cache=True)
#     def selected_variant(self) -> str: return self._selected_variant

#     @rx.var(cache=True)
#     def working_dict(self) -> dict[str, list[str]]: return self.variants[self.selected_variant]

#     # Event handlers
#     @rx.event
#     def double_click_event(self, cell_uid: str):
#         print("cell has been double clicked and we got ", cell_uid)
#         self.selected_cell = cell_uid

#     @rx.event
#     def lose_cell_focus(self):
#         self.selected_cell = ""

#     @rx.event
#     def set_select_value(self, value: str):
#         self._selected_variant = value

#     @rx.event
#     def on_add_column(self, info: dict):
#         column_name = info["column_name"]
#         self.variants[self.selected_variant][column_name] = [""] * self.num_rows
#         return rx.toast.info(
#             f"Added column: {column_name}",
#             position="bottom-right"
#         )
   
#     @rx.event
#     def on_remove_column(self, info: dict):
#         column_name = info["column_name"]
#         del self.variants[self.selected_variant][column_name]
#         return rx.toast.info(
#             f"Removed column: {column_name}",
#             position="bottom-right"
#         )
    
#     @rx.event
#     def update_cell(self, header: str, changes: str, index: int = None, row_idx: int = None, is_row_cell: bool = False):
#         value = changes
        
#         if is_row_cell:
#             self.variants[self.selected_variant][header][row_idx] = value
#         else:
#             new_dict = {}
#             for key in self.working_dict_headers:
#                 v = list(self.variants[self.selected_variant][key])  # Create new list copy
#                 if key == header:
#                     new_dict[value] = v
#                 else:
#                     new_dict[key] = v
#             self.variants[self.selected_variant] = new_dict
    
#         print(f"Updated value: {value}")
#         print(f"current headers: {list(self.variants[self.selected_variant].keys())}")

#     # Table creation methods
#     @classmethod
#     def craft_table_cell(self, content: str, header: str = None, index: int = None, row_idx: int = None, header_cell: bool = False):
#         cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
#         cell_uid = f"{self.selected_variant}-template-cell-{header}-{index}-{row_idx}-header?-{header_cell}"

#         return cell_component(
#             rx.box(
#                 rx.cond(
#                     self.selected_cell == cell_uid,
#                     rx.text_field(
#                         value=content,
#                         on_blur=lambda: self.lose_cell_focus(),
#                         autofocus=True,
#                         on_change=lambda changes: self.update_cell(header, changes, index, row_idx, not header_cell)
#                     ),
#                     rx.text(content)
#                 ),
#             ),
#             class_name="csv_data_cell",
#             on_double_click= lambda: self.double_click_event(cell_uid)
#         )

#     @classmethod
#     def get_component(cls, data: str = None, **props) -> rx.Component:
#         """Creating a csv data field component.
#         Params:
#             data: type 'str' which consists of a CSV-like string
#         """
#         return rx.flex(
#             # Select dropdown
#             rx.box(            
#                 rx.select(
#                     cls.variant_selections,
#                     value=cls.selected_variant,
#                     on_change=cls.set_select_value,
#                     variant="surface",
#                 )
#             ),
#             # Table and buttons container
#             rx.flex(
#                 rx.el.div(
#                     rx.table.root(
#                         rx.table.header(
#                             rx.table.row(
#                                 rx.foreach(
#                                     cls.working_dict_headers,
#                                     lambda header, index: cls.craft_table_cell(content=header, header=header, index=index, header_cell=True)
#                                 )
#                             )
#                         ),
#                         rx.table.body(
#                             rx.foreach(
#                                 cls.working_dict_rows,
#                                 lambda row, i: rx.table.row(
#                                     rx.foreach(
#                                         row,
#                                         lambda value, index: cls.craft_table_cell(
#                                             content=value, 
#                                             header=cls.working_dict_headers[index], 
#                                             index=index,
#                                             row_idx=i
#                                         )
#                                     )
#                                 )
#                             )
#                         ),
#                         width="40rem",
#                         height="25rem",
#                     ),
#                     class_name="config_template_config_container"
#                 ),
#                 # Container for dialog trigger buttons
#                 rx.flex(
#                     rx.dialog.root(
#                         rx.dialog.trigger(
#                             # rx.button(rx.icon("plus", size=30), variant="soft")
#                             add_icon_button.add_icon_button(
#                                 tool_tip_content="Add a new column"
#                             ),
#                         ),
#                         rx.dialog.content(
#                             rx.dialog.title(
#                                 "Add a new column"
#                             ),
#                             rx.form(
#                                 rx.flex(
#                                     form_entry.form_entry(
#                                         "Column Name",
#                                         rx.input(
#                                             name="column_name",
#                                             required=True
#                                         ),
#                                         required_entry=True
#                                     ),
#                                     rx.flex(
#                                         rx.dialog.close(
#                                             rx.button(
#                                                 "Cancel",
#                                                 variant="soft"
#                                             )
#                                         ),
#                                         rx.dialog.close(
#                                             rx.button(
#                                                 "Add",
#                                                 type="submit"
#                                             )
#                                         ),
#                                         spacing="3",
#                                         justify="end"
#                                     ),
#                                     direction="column",
#                                     spacing="6"
#                                 ),
#                                 on_submit=cls.on_add_column,
#                                 reset_on_submit=False,
#                             ),
#                             max_width="450px",
#                         )
#                     ),
#                     rx.dialog.root(
#                         rx.dialog.trigger(
#                             icon_button_wrapper.icon_button_wrapper(
#                                 tool_tip_content="Remove a column",
#                                 icon_key="minus"
#                             ),
#                         ),
#                         rx.dialog.content(
#                             rx.dialog.title(
#                                 "Remove a column"
#                             ),
#                             rx.form(
#                                 rx.flex(
#                                     form_entry.form_entry(
#                                         "Column Name",
#                                         rx.select(
#                                             cls.working_dict_headers,
#                                             name="column_name",
#                                             required=True
#                                         ),
#                                         required_entry=True
#                                     ),
#                                     rx.flex(
#                                         rx.dialog.close(
#                                             rx.button(
#                                                 "Cancel",
#                                                 variant="soft"
#                                             )
#                                         ),
#                                         rx.dialog.close(
#                                             rx.button(
#                                                 "Remove",
#                                                 color_scheme="red",
#                                                 type="submit"
#                                             )
#                                         ),
#                                         spacing="3",
#                                         justify="end"
#                                     ),
#                                     direction="column",
#                                     spacing="6"
#                                 ),
#                                 on_submit=cls.on_remove_column,
#                                 reset_on_submit=False,
#                             ),
#                             max_width="450px",
#                         )
#                     ),
#                     direction="column",
#                     spacing="4"
#                 ),
#                 direction="row",
#                 spacing="4"
#             ),
#             spacing="6",
#             direction="column"
#         )

# # Create component instance
# csv_data_field = CSVDataField.create

import reflex as rx
from typing import Dict, List, Optional
from ...model_views import ConfigStoreEntryModelView
from loguru import logger

class CSVDataState(rx.State):
    working_config_entry: ConfigStoreEntryModelView = ConfigStoreEntryModelView()
    selected_variant: str = "Default 1"
    selected_cell: str = ""
    num_rows: int = 10
    row_iter: list[int] = list(range(num_rows))
    show_add_dialog: bool = False
    show_remove_dialog: bool = False

    # Cached reactive vars
    @rx.var(cache=True)
    def variants(self) -> Dict[str, Dict[str, List[str]]]:
        return self.working_config_entry.csv_variants

    @rx.var(cache=True)
    def working_headers(self) -> List[str]:
        return list(self.variants[self.selected_variant].keys())

    @rx.var(cache=True)
    def working_rows(self) -> List[List[str]]:
        working_dict = self.variants[self.selected_variant]
        headers = list(working_dict.keys())
        return [[working_dict[header][i] for header in headers] 
                for i in range(self.num_rows)]

    # Event handlers
    @rx.event
    def double_click_event(self, cell_uid: str):
        logger.debug("cell has been double clicked and we got ", cell_uid)
        self.selected_cell = cell_uid

    @rx.event
    def lose_cell_focus(self):
        self.selected_cell = ""

    @rx.event
    def update_cell(self, header: str, changes: str, index: int = None, row_idx: int = None, is_row_cell: bool = False):
        value = changes
        
        if is_row_cell:
            self.working_config_entry.csv_variants[self.selected_variant][header][row_idx] = value
        else:
            # Update header name
            new_dict = {}
            for key in self.working_headers:
                v = list(self.variants[self.selected_variant][key])  # Create new list copy
                if key == header:
                    new_dict[value] = v
                else:
                    new_dict[key] = v
            self.working_config_entry.csv_variants[self.selected_variant] = new_dict

    @rx.event
    def set_variant(self, variant: str):
        self.selected_variant = variant

    @rx.event
    def add_column(self, form_data: dict):
        column_name = form_data["column_name"]
        self.working_config_entry.csv_variants[self.selected_variant][column_name] = [""] * self.num_rows
        self.show_add_dialog = False
        return rx.toast.info(f"Added column: {column_name}", position="bottom-right")

    @rx.event
    def remove_column(self, form_data: dict):
        column_name = form_data["column_name"]
        del self.working_config_entry.csv_variants[self.selected_variant][column_name]
        self.show_remove_dialog = False
        return rx.toast.info(f"Removed column: {column_name}", position="bottom-right")

    @rx.event
    def set_working_config(self, config_entry: ConfigStoreEntryModelView):
        """Sets the working config entry and initializes necessary state variables."""
        self.working_config_entry = config_entry
        
        logger.debug(f"i have set config entry with id: {self.working_config_entry.component_id}")
        # Initialize with first variant if available
        if config_entry.csv_variants:
            first_variant = next(iter(config_entry.csv_variants.keys()))
            self.selected_variant = first_variant
        
        # Update num_rows if needed
        if config_entry.csv_variants and config_entry.csv_variants[self.selected_variant]:
            first_column = next(iter(config_entry.csv_variants[self.selected_variant].values()))
            self.num_rows = len(first_column)
            self.row_iter = list(range(self.num_rows))


def craft_table_cell(content: str, header: str = None, index: int = None, row_idx: int = None, header_cell: bool = False):
    cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
    cell_uid = f"{CSVDataState.selected_variant}-template-cell-{header}-{index}-{row_idx}-header?-{header_cell}"
    return cell_component(
        rx.box(
            rx.cond(
                CSVDataState.selected_cell == cell_uid,
                rx.text_field(
                    value=content,
                    on_blur=CSVDataState.lose_cell_focus,
                    autofocus=True,
                    on_change=lambda changes: CSVDataState.update_cell(header, changes, index, row_idx, not header_cell)
                ),
                rx.text(content)
            ),
        ),
        class_name="csv_data_cell",
        on_double_click=lambda: CSVDataState.double_click_event(cell_uid)
    )

def csv_table():
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.foreach(
                    CSVDataState.working_headers,
                    lambda header, index: craft_table_cell(
                        content=header, 
                        header=header, 
                        index=index, 
                        header_cell=True
                    )
                )
            )
        ),
        rx.table.body(
            rx.foreach(
                CSVDataState.working_rows,
                lambda row, i: rx.table.row(
                    rx.foreach(
                        row,
                        lambda value, index: craft_table_cell(
                            content=value, 
                            header=CSVDataState.working_headers[index], 
                            index=index,
                            row_idx=i
                        )
                    )
                )
            )
        ),
        width="40rem",
        height="25rem",
    )

def add_column_dialog():
    return rx.dialog.root(
        rx.dialog.trigger(
            add_icon_button.add_icon_button(
                tool_tip_content="Add a new column"
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Add a new column"),
            rx.form(
                rx.flex(
                    form_entry.form_entry(
                        "Column Name",
                        rx.input(
                            name="column_name",
                            required=True
                        ),
                        required_entry=True
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button(
                                "Cancel",
                                variant="soft"
                            )
                        ),
                        rx.dialog.close(
                            rx.button(
                                "Add",
                                type="submit"
                            )
                        ),
                        spacing="3",
                        justify="end"
                    ),
                    direction="column",
                    spacing="6"
                ),
                on_submit=CSVDataState.add_column,
                reset_on_submit=False,
            ),
            max_width="450px",
        )
    )

def remove_column_dialog():
    return rx.dialog.root(
        rx.dialog.trigger(
            icon_button_wrapper.icon_button_wrapper(
                tool_tip_content="Remove a column",
                icon_key="minus"
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Remove a column"),
            rx.form(
                rx.flex(
                    form_entry.form_entry(
                        "Column Name",
                        rx.select(
                            CSVDataState.working_headers,
                            name="column_name",
                            required=True
                        ),
                        required_entry=True
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button(
                                "Cancel",
                                variant="soft"
                            )
                        ),
                        rx.dialog.close(
                            rx.button(
                                "Remove",
                                color_scheme="red",
                                type="submit"
                            )
                        ),
                        spacing="3",
                        justify="end"
                    ),
                    direction="column",
                    spacing="6"
                ),
                on_submit=CSVDataState.remove_column,
                reset_on_submit=False,
            ),
            max_width="450px",
        )
    )

def csv_data_field(config: ConfigStoreEntryModelView = False):

    return rx.cond(CSVDataState.is_hydrated, rx.flex(
        rx.box(
            rx.select(
                CSVDataState.variants.keys(),
                value=CSVDataState.selected_variant,
                on_change=CSVDataState.set_variant,
                variant="surface",
            )
        ),
        rx.flex(
            rx.el.div(
                csv_table(),
                class_name="config_template_config_container"
            ),
            rx.flex(
                add_column_dialog(),
                rx.divider(),
                remove_column_dialog(),
                direction="column",
                spacing="4"
            ),
            direction="row",
            spacing="4"
        ),
        spacing="6",
        direction="column",
        # on_mount=lambda: CSVDataState.set_working_config(config)
        on_mount=lambda: CSVDataState.set_working_config(ConfigStoreEntryModelView())
    ),
    rx.spinner(height="100vh"))