import reflex as rx
from ..buttons import add_icon_button, icon_button_wrapper
from ..form_components import form_entry
from typing import Dict, List, Optional
from ...model_views import ConfigStoreEntryModelView
from loguru import logger
#version 1
from ..form_components import form_entry

# class CSVDataField(rx.ComponentState):
    # _selected_variant: str = "Default 1"  # Internal state
    # num_rows: int = 10
    # _row_iter: list[int] = list(range(num_rows))
    # working_config_entry: ConfigStoreEntryModelView = ConfigStoreEntryModelView() 

    # roar: str = ""
    # selected_cell: str = ""

    # # Reactive vars
    # @rx.var(cache=True)
    # def working_dict_headers(self) -> list[str]: return list(self.variants[self.selected_variant].keys())

    # @rx.var(cache=True)
    # def variant_selections(self) -> list[str]: return list(self.variants.keys())

    # @rx.var(cache=True)
    # def variants(self)-> dict[str, dict[str, list[str]]]:
    #     return self.working_config_entry.csv_variants

    # @rx.var(cache=True)
    # def working_dict_rows(self) -> list[list[str]]:
    #     # Accessing our dict values horizontally:
    #     working_dict = self.variants[self.selected_variant]
    #     headers = list(working_dict.keys())

    #     num_rows = len(list(working_dict.values())[0])
    #     rows = []

    #     for i in range(num_rows):
    #         row = [working_dict[header][i] for header in headers]
    #         rows.append(row)

    #     return rows

    # @rx.var(cache=True)
    # def selected_variant(self) -> str: return self._selected_variant

    # @rx.var(cache=True)
    # def working_dict(self) -> dict[str, list[str]]: return self.variants[self.selected_variant]

    # # Event handlers
    # @rx.event
    # def double_click_event(self, cell_uid: str):
    #     logger.debug("cell has been double clicked and we got: {cell_uid}")
    #     self.selected_cell = cell_uid

    # @rx.event
    # def lose_cell_focus(self):
    #     self.selected_cell = ""

    # @rx.event
    # def set_select_value(self, value: str):
    #     self._selected_variant = value

    # @rx.event
    # def on_add_column(self, info: dict):
    #     column_name = info["column_name"]
    #     self.variants[self.selected_variant][column_name] = [""] * self.num_rows
    #     return rx.toast.info(
    #         f"Added column: {column_name}",
    #         position="bottom-right"
    #     )

    # @rx.event
    # def on_remove_column(self, info: dict):
    #     column_name = info["column_name"]
    #     del self.variants[self.selected_variant][column_name]
    #     return rx.toast.info(
    #         f"Removed column: {column_name}",
    #         position="bottom-right"
    #     )

    # @rx.event
    # def update_cell(self, header: str, changes: str, index: int = None, row_idx: int = None, is_row_cell: bool = False):
    #     value = changes

    #     if is_row_cell:
    #         self.variants[self.selected_variant][header][row_idx] = value
    #     else:
    #         new_dict = {}
    #         for key in self.working_dict_headers:
    #             v = list(self.variants[self.selected_variant][key])  # Create new list copy
    #             if key == header:
    #                 new_dict[value] = v
    #             else:
    #                 new_dict[key] = v
    #         self.variants[self.selected_variant] = new_dict

    #     logger.debug(f"Updated value: {value}")
    #     logger.debug(f"current headers: {list(self.variants[self.selected_variant].keys())}")

    # @rx.event
    # def refresh_component(self, config: ConfigStoreEntryModelView):
    #     self.working_config_entry = config
    #     logger.debug(f"new working config: {self.working_config_entry}")

    # @rx.event
    # def yay(self, config=False):
    #     logger.debug(f"yellow there: {self.roar}")

    # # Table creation methods
    # @classmethod
    # def craft_table_cell(self, content: str, header: str = None, index: int = None, row_idx: int = None, header_cell: bool = False):
    #     cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
    #     cell_uid = f"{self.selected_variant}-template-cell-{header}-{index}-{row_idx}-header?-{header_cell}"

    #     return cell_component(
    #         rx.box(
    #             rx.cond(
    #                 self.selected_cell == cell_uid,
    #                 rx.text_field(
    #                     value=content,
    #                     on_blur=lambda: self.lose_cell_focus(),
    #                     autofocus=True,
    #                     on_change=lambda changes: self.update_cell(header, changes, index, row_idx, not header_cell)
    #                 ),
    #                 rx.text(content)
    #             ),
    #         ),
    #         class_name="csv_data_cell",
    #         on_double_click= lambda: self.double_click_event(cell_uid)
    #     )

    # @classmethod
    # def get_component(cls, data: ConfigStoreEntryModelView, **props) -> rx.Component:
    #     """Creating a csv data field component.
    #     Params:
    #         data: type 'str' which consists of a CSV-like string
    #     """
    #     # if data is not None:
    #     #     logger.debug(f"here is the data i passed in: {data}")
    #     cls.roar = data
    #     logger.debug(f"this is my passed in data: {cls.roar}")

    #     return rx.fragment(
    #     rx.flex(
    #         # Select dropdown
    #         rx.box(            
    #             rx.select(
    #                 cls.variant_selections,
    #                 value=cls.selected_variant,
    #                 on_change=cls.set_select_value,
    #                 variant="surface",
    #             )
    #         ),
    #         # Table and buttons container
    #         rx.flex(
    #             rx.el.div(
    #                 rx.table.root(
    #                     rx.table.header(
    #                         rx.table.row(
    #                             rx.foreach(
    #                                 cls.working_dict_headers,
    #                                 lambda header, index: cls.craft_table_cell(content=header, header=header, index=index, header_cell=True)
    #                             )
    #                         )
    #                     ),
    #                     rx.table.body(
    #                         rx.foreach(
    #                             cls.working_dict_rows,
    #                             lambda row, i: rx.table.row(
    #                                 rx.foreach(
    #                                     row,
    #                                     lambda value, index: cls.craft_table_cell(
    #                                         content=value, 
    #                                         header=cls.working_dict_headers[index], 
    #                                         index=index,
    #                                         row_idx=i
    #                                     )
    #                                 )
    #                             )
    #                         )
    #                     ),
    #                     width="40rem",
    #                     height="25rem",
    #                 ),
    #                 class_name="config_template_config_container"
    #             ),
    #             # Container for dialog trigger buttons
    #             rx.flex(
    #                 rx.dialog.root(
    #                     rx.dialog.trigger(
    #                         # rx.button(rx.icon("plus", size=30), variant="soft")
    #                         add_icon_button.add_icon_button(
    #                             tool_tip_content="Add a new column"
    #                         ),
    #                     ),
    #                     rx.dialog.content(
    #                         rx.dialog.title(
    #                             "Add a new column"
    #                         ),
    #                         rx.form(
    #                             rx.flex(
    #                                 form_entry.form_entry(
    #                                     "Column Name",
    #                                     rx.input(
    #                                         name="column_name",
    #                                         required=True
    #                                     ),
    #                                     required_entry=True
    #                                 ),
    #                                 rx.flex(
    #                                     rx.dialog.close(
    #                                         rx.button(
    #                                             "Cancel",
    #                                             variant="soft"
    #                                         )
    #                                     ),
    #                                     rx.dialog.close(
    #                                         rx.button(
    #                                             "Add",
    #                                             type="submit"
    #                                         )
    #                                     ),
    #                                     spacing="3",
    #                                     justify="end"
    #                                 ),
    #                                 direction="column",
    #                                 spacing="6"
    #                             ),
    #                             on_submit=cls.on_add_column,
    #                             reset_on_submit=False,
    #                         ),
    #                         max_width="450px",
    #                     )
    #                 ),
    #                 rx.dialog.root(
    #                     rx.dialog.trigger(
    #                         icon_button_wrapper.icon_button_wrapper(
    #                             tool_tip_content="Remove a column",
    #                             icon_key="minus"
    #                         ),
    #                     ),
    #                     rx.dialog.content(
    #                         rx.dialog.title(
    #                             "Remove a column"
    #                         ),
    #                         rx.form(
    #                             rx.flex(
    #                                 form_entry.form_entry(
    #                                     "Column Name",
    #                                     rx.select(
    #                                         cls.working_dict_headers,
    #                                         name="column_name",
    #                                         required=True
    #                                     ),
    #                                     required_entry=True
    #                                 ),
    #                                 rx.flex(
    #                                     rx.dialog.close(
    #                                         rx.button(
    #                                             "Cancel",
    #                                             variant="soft"
    #                                         )
    #                                     ),
    #                                     rx.dialog.close(
    #                                         rx.button(
    #                                             "Remove",
    #                                             color_scheme="red",
    #                                             type="submit"
    #                                         )
    #                                     ),
    #                                     spacing="3",
    #                                     justify="end"
    #                                 ),
    #                                 direction="column",
    #                                 spacing="6"
    #                             ),
    #                             on_submit=cls.on_remove_column,
    #                             reset_on_submit=False,
    #                         ),
    #                         max_width="450px",
    #                     )
    #                 ),
    #                 direction="column",
    #                 spacing="4"
    #             ),
    #             direction="row",
    #             spacing="4"
    #         ),
    #         spacing="6",
    #         direction="column",
    #         on_mount=cls.yay
    #     ))

# Create component instance
# csv_data_table = CSVDataField.create

# Version 2
# class CSVDataState(rx.State):
#     tables: dict[str, ConfigStoreEntryModelView] = {}
#     working_config_entry: ConfigStoreEntryModelView = ConfigStoreEntryModelView()
#     selected_variant: str = "Default 1"
#     selected_cell: str = ""
#     num_rows: int = 10
#     row_iter: list[int] = list(range(num_rows))
#     show_add_dialog: bool = False
#     show_remove_dialog: bool = False
#     working_table_id: str = ""

#     chills: str = ""

#     # Cached reactive vars
#     rx.var(cache=True)
#     def working_config(self) -> ConfigStoreEntryModelView:
#         return self.tables[self.working_table_id]

#     @rx.var(cache=True)
#     def variants(self) -> dict[str, dict[str, list[str]]]:
#         return self.working_config_entry.csv_variants

#     @rx.var(cache=True)
#     def working_headers(self) -> list[str]:
#         return list(self.variants[self.selected_variant].keys())

#     @rx.var(cache=True)
#     def working_rows(self) -> list[list[str]]:
#         working_dict = self.variants[self.selected_variant]
#         headers = list(working_dict.keys())
#         return [[working_dict[header][i] for header in headers] 
#                 for i in range(self.num_rows)]

#     # Event handlers
#     @rx.event
#     def double_click_event(self, cell_uid: str):
#         logger.debug("cell has been double clicked and we got ", cell_uid)
#         self.selected_cell = cell_uid

#     @rx.event
#     def lose_cell_focus(self):
#         self.selected_cell = ""

#     @rx.event
#     def update_cell(self, header: str, changes: str, index: int = None, row_idx: int = None, is_row_cell: bool = False):
#         value = changes
        
#         if is_row_cell:
#             self.working_config_entry.csv_variants[self.selected_variant][header][row_idx] = value
#         else:
#             # Update header name
#             new_dict = {}
#             for key in self.working_headers:
#                 v = list(self.variants[self.selected_variant][key])  # Create new list copy
#                 if key == header:
#                     new_dict[value] = v
#                 else:
#                     new_dict[key] = v
#             self.working_config_entry.csv_variants[self.selected_variant] = new_dict

#     @rx.event
#     def set_variant(self, variant: str):
#         self.selected_variant = variant
#         logger.debug(f"can we print out self.chills: {self.chills}")
#         logger.debug(f"can we print out self.selected_variant?: {self.selected_variant}")

#     @rx.event
#     def add_column(self, form_data: dict):
#         column_name = form_data["column_name"]
#         self.working_config_entry.csv_variants[self.selected_variant][column_name] = [""] * self.num_rows
#         self.show_add_dialog = False
#         return rx.toast.info(f"Added column: {column_name}", position="bottom-right")

#     @rx.event
#     def remove_column(self, form_data: dict):
#         column_name = form_data["column_name"]
#         del self.working_config_entry.csv_variants[self.selected_variant][column_name]
#         self.show_remove_dialog = False
#         return rx.toast.info(f"Removed column: {column_name}", position="bottom-right")

#     @rx.event
#     def set_working_config(self, config_entry):
#         """Sets the working config entry and initializes necessary state variables."""
#         # self.working_config_entry = config_entry
        
#         logger.debug(f"i have set config entry with id: {config_entry}")
#         # # Initialize with first variant if available
#         # if config_entry.csv_variants:
#         #     first_variant = next(iter(config_entry.csv_variants.keys()))
#         #     self.selected_variant = first_variant
        
#         # # Update num_rows if needed
#         # if config_entry.csv_variants and config_entry.csv_variants[self.selected_variant]:
#         #     first_column = next(iter(config_entry.csv_variants[self.selected_variant].values()))
#         #     self.num_rows = len(first_column)
#         #     self.row_iter = list(range(self.num_rows))

#     @rx.event
#     def refresh_state(self):
#         logger.debug("hello its me ")
#         # self.tables[config.component_id] = config
#         # self.working_table_id = config.component_id


# def craft_table_cell(content: str, header: str = None, index: int = None, row_idx: int = None, header_cell: bool = False):
#     cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
#     cell_uid = f"{CSVDataState.selected_variant}-template-cell-{header}-{index}-{row_idx}-header?-{header_cell}"
#     return cell_component(
#         rx.box(
#             rx.cond(
#                 CSVDataState.selected_cell == cell_uid,
#                 rx.text_field(
#                     value=content,
#                     on_blur=CSVDataState.lose_cell_focus,
#                     autofocus=True,
#                     on_change=lambda changes: CSVDataState.update_cell(header, changes, index, row_idx, not header_cell)
#                 ),
#                 rx.text(content)
#             ),
#         ),
#         class_name="csv_data_cell",
#         on_double_click=lambda: CSVDataState.double_click_event(cell_uid)
#     )

# def csv_table():
#     return rx.table.root(
#         rx.table.header(
#             rx.table.row(
#                 rx.foreach(
#                     CSVDataState.working_headers,
#                     lambda header, index: craft_table_cell(
#                         content=header, 
#                         header=header, 
#                         index=index, 
#                         header_cell=True
#                     )
#                 )
#             )
#         ),
#         rx.table.body(
#             rx.foreach(
#                 CSVDataState.working_rows,
#                 lambda row, i: rx.table.row(
#                     rx.foreach(
#                         row,
#                         lambda value, index: craft_table_cell(
#                             content=value, 
#                             header=CSVDataState.working_headers[index], 
#                             index=index,
#                             row_idx=i
#                         )
#                     )
#                 )
#             )
#         ),
#         width="40rem",
#         height="25rem",
#     )

# def add_column_dialog():
#     return rx.dialog.root(
#         rx.dialog.trigger(
#             add_icon_button.add_icon_button(
#                 tool_tip_content="Add a new column"
#             ),
#         ),
#         rx.dialog.content(
#             rx.dialog.title("Add a new column"),
#             rx.form(
#                 rx.flex(
#                     form_entry.form_entry(
#                         "Column Name",
#                         rx.input(
#                             name="column_name",
#                             required=True
#                         ),
#                         required_entry=True
#                     ),
#                     rx.flex(
#                         rx.dialog.close(
#                             rx.button(
#                                 "Cancel",
#                                 variant="soft"
#                             )
#                         ),
#                         rx.dialog.close(
#                             rx.button(
#                                 "Add",
#                                 type="submit"
#                             )
#                         ),
#                         spacing="3",
#                         justify="end"
#                     ),
#                     direction="column",
#                     spacing="6"
#                 ),
#                 on_submit=CSVDataState.add_column,
#                 reset_on_submit=False,
#             ),
#             max_width="450px",
#         )
#     )

# def remove_column_dialog():
#     return rx.dialog.root(
#         rx.dialog.trigger(
#             icon_button_wrapper.icon_button_wrapper(
#                 tool_tip_content="Remove a column",
#                 icon_key="minus"
#             ),
#         ),
#         rx.dialog.content(
#             rx.dialog.title("Remove a column"),
#             rx.form(
#                 rx.flex(
#                     form_entry.form_entry(
#                         "Column Name",
#                         rx.select(
#                             CSVDataState.working_headers,
#                             name="column_name",
#                             required=True
#                         ),
#                         required_entry=True
#                     ),
#                     rx.flex(
#                         rx.dialog.close(
#                             rx.button(
#                                 "Cancel",
#                                 variant="soft"
#                             )
#                         ),
#                         rx.dialog.close(
#                             rx.button(
#                                 "Remove",
#                                 color_scheme="red",
#                                 type="submit"
#                             )
#                         ),
#                         spacing="3",
#                         justify="end"
#                     ),
#                     direction="column",
#                     spacing="6"
#                 ),
#                 on_submit=CSVDataState.remove_column,
#                 reset_on_submit=False,
#             ),
#             max_width="450px",
#         )
#     )

# def csv_data_field() -> rx.Component:


#     return rx.cond(CSVDataState.is_hydrated, rx.flex(
#         rx.box(
#             rx.select(
#                 CSVDataState.variants.keys(),
#                 value=CSVDataState.selected_variant,
#                 on_change=CSVDataState.set_variant,
#                 variant="surface",
#             )
#         ),
#         rx.flex(
#             rx.el.div(
#                 csv_table(),
#                 class_name="config_template_config_container"
#             ),
#             rx.flex(
#                 add_column_dialog(),
#                 rx.divider(),
#                 remove_column_dialog(),
#                 direction="column",
#                 spacing="4"
#             ),
#             direction="row",
#             spacing="4"
#         ),
#         spacing="6",
#         direction="column",
#     ),
#     rx.spinner(height="100vh"))



# Version 2
# class CSVDataState(rx.State):
#     working_config_entry: ConfigStoreEntryModelView = ConfigStoreEntryModelView()
#     selected_variant: str = "Default 1"
#     selected_cell: str = ""
#     num_rows: int = 10
#     row_iter: list[int] = list(range(num_rows))
#     show_add_dialog: bool = False
#     show_remove_dialog: bool = False

#     # Cached reactive vars
#     @rx.var(cache=True)
#     def variants(self) -> dict[str, dict[str, list[str]]]:
#         return self.working_config_entry.csv_variants

#     @rx.var(cache=True)
#     def working_headers(self) -> list[str]:
#         return list(self.variants[self.selected_variant].keys())

#     @rx.var(cache=True)
#     def working_rows(self) -> list[list[str]]:
#         working_dict = self.variants[self.selected_variant]
#         headers = list(working_dict.keys())
#         return [[working_dict[header][i] for header in headers] 
#                 for i in range(self.num_rows)]

#     # Event handlers
#     @rx.event
#     def double_click_event(self, cell_uid: str):
#         logger.debug("cell has been double clicked and we got ", cell_uid)
#         self.selected_cell = cell_uid

#     @rx.event
#     def lose_cell_focus(self):
#         self.selected_cell = ""

#     @rx.event
#     def update_cell(self, header: str, changes: str, index: int = None, row_idx: int = None, is_row_cell: bool = False):
#         value = changes
        
#         if is_row_cell:
#             self.working_config_entry.csv_variants[self.selected_variant][header][row_idx] = value
#         else:
#             # Update header name
#             new_dict = {}
#             for key in self.working_headers:
#                 v = list(self.variants[self.selected_variant][key])  # Create new list copy
#                 if key == header:
#                     new_dict[value] = v
#                 else:
#                     new_dict[key] = v
#             self.working_config_entry.csv_variants[self.selected_variant] = new_dict

#     @rx.event
#     def set_variant(self, variant: str):
#         self.selected_variant = variant

#     @rx.event
#     def add_column(self, form_data: dict):
#         column_name = form_data["column_name"]
#         self.working_config_entry.csv_variants[self.selected_variant][column_name] = [""] * self.num_rows
#         self.show_add_dialog = False
#         return rx.toast.info(f"Added column: {column_name}", position="bottom-right")

#     @rx.event
#     def remove_column(self, form_data: dict):
#         column_name = form_data["column_name"]
#         del self.working_config_entry.csv_variants[self.selected_variant][column_name]
#         self.show_remove_dialog = False
#         return rx.toast.info(f"Removed column: {column_name}", position="bottom-right")

#     @rx.event
#     def set_working_config(self, config_entry):
#         """Sets the working config entry and initializes necessary state variables."""
#         # self.working_config_entry = config_entry
        
#         logger.debug(f"i have set config entry with id: {config_entry}")
#         # # Initialize with first variant if available
#         # if config_entry.csv_variants:
#         #     first_variant = next(iter(config_entry.csv_variants.keys()))
#         #     self.selected_variant = first_variant
        
#         # # Update num_rows if needed
#         # if config_entry.csv_variants and config_entry.csv_variants[self.selected_variant]:
#         #     first_column = next(iter(config_entry.csv_variants[self.selected_variant].values()))
#         #     self.num_rows = len(first_column)
#         #     self.row_iter = list(range(self.num_rows))

# def craft_table_cell(content: str, header: str = None, index: int = None, row_idx: int = None, header_cell: bool = False):
#     cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
#     cell_uid = f"{CSVDataState.selected_variant}-template-cell-{header}-{index}-{row_idx}-header?-{header_cell}"
#     return cell_component(
#         rx.box(
#             rx.cond(
#                 CSVDataState.selected_cell == cell_uid,
#                 rx.text_field(
#                     value=content,
#                     on_blur=CSVDataState.lose_cell_focus,
#                     autofocus=True,
#                     on_change=lambda changes: CSVDataState.update_cell(header, changes, index, row_idx, not header_cell)
#                 ),
#                 rx.text(content)
#             ),
#         ),
#         class_name="csv_data_cell",
#         on_double_click=lambda: CSVDataState.double_click_event(cell_uid)
#     )

# def csv_table():
#     return rx.table.root(
#         rx.table.header(
#             rx.table.row(
#                 rx.foreach(
#                     CSVDataState.working_headers,
#                     lambda header, index: craft_table_cell(
#                         content=header, 
#                         header=header, 
#                         index=index, 
#                         header_cell=True
#                     )
#                 )
#             )
#         ),
#         rx.table.body(
#             rx.foreach(
#                 CSVDataState.working_rows,
#                 lambda row, i: rx.table.row(
#                     rx.foreach(
#                         row,
#                         lambda value, index: craft_table_cell(
#                             content=value, 
#                             header=CSVDataState.working_headers[index], 
#                             index=index,
#                             row_idx=i
#                         )
#                     )
#                 )
#             )
#         ),
#         width="40rem",
#         height="25rem",
#     )

# def add_column_dialog():
#     return rx.dialog.root(
#         rx.dialog.trigger(
#             add_icon_button.add_icon_button(
#                 tool_tip_content="Add a new column"
#             ),
#         ),
#         rx.dialog.content(
#             rx.dialog.title("Add a new column"),
#             rx.form(
#                 rx.flex(
#                     form_entry.form_entry(
#                         "Column Name",
#                         rx.input(
#                             name="column_name",
#                             required=True
#                         ),
#                         required_entry=True
#                     ),
#                     rx.flex(
#                         rx.dialog.close(
#                             rx.button(
#                                 "Cancel",
#                                 variant="soft"
#                             )
#                         ),
#                         rx.dialog.close(
#                             rx.button(
#                                 "Add",
#                                 type="submit"
#                             )
#                         ),
#                         spacing="3",
#                         justify="end"
#                     ),
#                     direction="column",
#                     spacing="6"
#                 ),
#                 on_submit=CSVDataState.add_column,
#                 reset_on_submit=False,
#             ),
#             max_width="450px",
#         )
#     )

# def remove_column_dialog():
#     return rx.dialog.root(
#         rx.dialog.trigger(
#             icon_button_wrapper.icon_button_wrapper(
#                 tool_tip_content="Remove a column",
#                 icon_key="minus"
#             ),
#         ),
#         rx.dialog.content(
#             rx.dialog.title("Remove a column"),
#             rx.form(
#                 rx.flex(
#                     form_entry.form_entry(
#                         "Column Name",
#                         rx.select(
#                             CSVDataState.working_headers,
#                             name="column_name",
#                             required=True
#                         ),
#                         required_entry=True
#                     ),
#                     rx.flex(
#                         rx.dialog.close(
#                             rx.button(
#                                 "Cancel",
#                                 variant="soft"
#                             )
#                         ),
#                         rx.dialog.close(
#                             rx.button(
#                                 "Remove",
#                                 color_scheme="red",
#                                 type="submit"
#                             )
#                         ),
#                         spacing="3",
#                         justify="end"
#                     ),
#                     direction="column",
#                     spacing="6"
#                 ),
#                 on_submit=CSVDataState.remove_column,
#                 reset_on_submit=False,
#             ),
#             max_width="450px",
#         )
#     )

# def csv_data_field(config: ConfigStoreEntryModelView = False):

#     logger.debug(f"passed into data_field: {config}")
#     # CSVDataField.working_config_entry = config
#     return rx.cond(CSVDataState.is_hydrated, rx.flex(
#         rx.box(
#             rx.select(
#                 CSVDataState.variants.keys(),
#                 value=CSVDataState.selected_variant,
#                 on_change=CSVDataState.set_variant,
#                 variant="surface",
#             )
#         ),
#         rx.flex(
#             rx.el.div(
#                 csv_table(),
#                 class_name="config_template_config_container"
#             ),
#             rx.flex(
#                 add_column_dialog(),
#                 rx.divider(),
#                 remove_column_dialog(),
#                 direction="column",
#                 spacing="4"
#             ),
#             direction="row",
#             spacing="4"
#         ),
#         spacing="6",
#         direction="column",
#         # on_mount=lambda: CSVDataState.set_working_config(config)
#         # on_mount=lambda: CSVDataState.set_working_config(ConfigStoreEntryModelView())
#     ),
#     rx.spinner(height="100vh"))


# class CSVTableState(rx.State):
#     table_states: dict[str, dict] = {}
#     current_config_id: str = ""

#     @rx.var
#     def current_state(self) -> dict[str, str]:
#         return self.table_states.get(self.current_config_id, {})

#     @rx.event
#     def init_table(self, config_id: str, config: ConfigStoreEntryModelView):
#         if config_id not in self.table_states:
#             self.table_states[config_id] = {
#                 "working_config_entry": config,
#                 "selected_variant": "Default 1",
#                 "selected_cell": "",
#                 "num_rows": 10,
#                 "row_iter": list(range(10)),
#                 "show_add_dialog": False,
#                 "show_remove_dialog": False
#             }
#         self.update_current_config_id(config_id)

#     @rx.event
#     def update_current_config_id(self, config_id: str):
#         self.table_states.current_config_id = config_id

#     @rx.event
#     def update_table_field(self, field: str, value):
#         if self.current_config_id in self.table_states:
#             self.table_states[self.current_config_id][field] = value






# class CSVDataState(rx.State):
#     @rx.var
#     def current_state(self) -> dict:
#         return CSVTableState.current_state

#     @rx.var
#     def variants(self) -> dict[str, dict[str, list[str]]]:
#         if self.current_state:
#             return self.current_state["working_config_entry"].csv_variants
#         return {}

#     @rx.var
#     def variant_keys(self) -> list[str]:
#         return list(self.variants.keys())

#     @rx.var
#     def working_headers(self) -> list[str]:
#         if self.variants:
#             return list(self.variants[self.current_state["selected_variant"]].keys())
#         return []

#     @rx.var
#     def working_rows(self) -> list[list[str]]:
#         if self.variants and self.current_state:
#             working_dict = self.variants[self.current_state["selected_variant"]]
#             headers = list(working_dict.keys())
#             return [[working_dict[header][i] for header in headers]
#                     for i in range(self.current_state["num_rows"])]
#         return []

#     # Event handlers
#     @rx.event
#     def double_click_event(self, cell_uid: str):
#         logger.debug(f"Cell has been double clicked and we got: {cell_uid}")
#         CSVTableState.update_table_field('selected_cell', cell_uid)

#     @rx.event
#     def lose_cell_focus(self):
#         CSVTableState.update_table_field('selected_cell', "")

#     @rx.event
#     def update_cell(self, header: str, changes: str, index: int = None, row_idx: int = None, is_row_cell: bool = False):
#         value = changes
#         state = CSVTableState.current_state

#         if is_row_cell:
#             state["working_config_entry"].csv_variants[state["selected_variant"]][header][row_idx] = value
#         else:
#             # Update header name
#             new_dict = {}
#             for key in self.working_headers:
#                 v = list(self.variants[state["selected_variant"]][key])  # Create new list copy
#                 if key == header:
#                     new_dict[value] = v
#                 else:
#                     new_dict[key] = v
#             state["working_config_entry"].csv_variants[state["selected_variant"]] = new_dict

#     @rx.event
#     def set_variant(self, variant: str):
#         CSVTableState.update_table_field('selected_variant', variant)

#     @rx.event
#     def add_column(self, form_data: dict):
#         column_name = form_data["column_name"]
#         state = CSVTableState.current_state
#         state["working_config_entry"].csv_variants[state["selected_variant"]][column_name] = [""] * state["num_rows"]
#         CSVTableState.update_table_field('show_add_dialog', False)
#         return rx.toast.info(f"Added column: {column_name}", position="bottom-right")

#     @rx.event
#     def remove_column(self, form_data: dict):
#         column_name = form_data["column_name"]
#         state = CSVTableState.current_state
#         del state["working_config_entry"].csv_variants[state["selected_variant"]][column_name]
#         CSVTableState.update_table_field('show_remove_dialog', False)
#         return rx.toast.info(f"Removed column: {column_name}", position="bottom-right")

#     @rx.event
#     def set_working_config(self, config_entry: ConfigStoreEntryModelView):
#         """Sets the working config entry and initializes necessary state variables."""
#         config_id = str(config_entry.component_id)
#         CSVTableState.init_table(config_id, config_entry)

# def craft_table_cell(content: str, header: str = None, index: int = None, row_idx: int = None, header_cell: bool = False):
#     cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
#     cell_uid = f"{CSVDataState.current_state['selected_variant']}-template-cell-{header}-{index}-{row_idx}-header?-{header_cell}"
#     return cell_component(
#         rx.box(
#             rx.cond(
#                 CSVDataState.current_state['selected_cell'] == cell_uid,
#                 rx.text_field(
#                     value=content,
#                     on_blur=CSVDataState.lose_cell_focus,
#                     autofocus=True,
#                     on_change=lambda changes: CSVDataState.update_cell(header, changes, index, row_idx, not header_cell)
#                 ),
#                 rx.text(content)
#             ),
#         ),
#         class_name="csv_data_cell",
#         on_double_click=lambda: CSVDataState.double_click_event(cell_uid)
#     )

# def csv_table():
#     return rx.table.root(
#         rx.table.header(
#             rx.table.row(
#                 rx.foreach(
#                     CSVDataState.working_headers,
#                     lambda header, index: craft_table_cell(
#                         content=header, 
#                         header=header, 
#                         index=index, 
#                         header_cell=True
#                     )
#                 )
#             )
#         ),
#         rx.table.body(
#             rx.foreach(
#                 CSVDataState.working_rows,
#                 lambda row, i: rx.table.row(
#                     rx.foreach(
#                         row,
#                         lambda value, index: craft_table_cell(
#                             content=value, 
#                             header=CSVDataState.working_headers[index], 
#                             index=index,
#                             row_idx=i
#                         )
#                     )
#                 )
#             )
#         ),
#         width="40rem",
#         height="25rem",
#     )

# def add_column_dialog():
#     return rx.dialog.root(
#         rx.dialog.trigger(
#             add_icon_button.add_icon_button(
#                 tool_tip_content="Add a new column"
#             ),
#         ),
#         rx.dialog.content(
#             rx.dialog.title("Add a new column"),
#             rx.form(
#                 rx.flex(
#                     form_entry.form_entry(
#                         "Column Name",
#                         rx.input(
#                             name="column_name",
#                             required=True
#                         ),
#                         required_entry=True
#                     ),
#                     rx.flex(
#                         rx.dialog.close(
#                             rx.button(
#                                 "Cancel",
#                                 variant="soft"
#                             )
#                         ),
#                         rx.dialog.close(
#                             rx.button(
#                                 "Add",
#                                 type="submit"
#                             )
#                         ),
#                         spacing="3",
#                         justify="end"
#                     ),
#                     direction="column",
#                     spacing="6"
#                 ),
#                 on_submit=CSVDataState.add_column,
#                 reset_on_submit=False,
#             ),
#             max_width="450px",
#         )
#     )

# def remove_column_dialog():
#     return rx.dialog.root(
#         rx.dialog.trigger(
#             icon_button_wrapper.icon_button_wrapper(
#                 tool_tip_content="Remove a column",
#                 icon_key="minus"
#             ),
#         ),
#         rx.dialog.content(
#             rx.dialog.title("Remove a column"),
#             rx.form(
#                 rx.flex(
#                     form_entry.form_entry(
#                         "Column Name",
#                         rx.select(
#                             CSVDataState.working_headers,
#                             name="column_name",
#                             required=True
#                         ),
#                         required_entry=True
#                     ),
#                     rx.flex(
#                         rx.dialog.close(
#                             rx.button(
#                                 "Cancel",
#                                 variant="soft"
#                             )
#                         ),
#                         rx.dialog.close(
#                             rx.button(
#                                 "Remove",
#                                 color_scheme="red",
#                                 type="submit"
#                             )
#                         ),
#                         spacing="3",
#                         justify="end"
#                     ),
#                     direction="column",
#                     spacing="6"
#                 ),
#                 on_submit=CSVDataState.remove_column,
#                 reset_on_submit=False,
#             ),
#             max_width="450px",
#         )
#     )

# def csv_data_field(config: ConfigStoreEntryModelView = None):
#     logger.debug(f"passed into data_field: {config}")
#     CSVDataState.set_working_config(config)
#     return rx.cond(
#         CSVDataState.is_hydrated, 
#         rx.flex(
#             rx.box(
#                 rx.select(
#                     CSVDataState.variant_keys,
#                     value=CSVDataState.current_state["selected_variant"],
#                     on_change=CSVDataState.set_variant,
#                     variant="surface",
#                 )
#             ),
#             rx.flex(
#                 rx.el.div(
#                     csv_table(),
#                     class_name="config_template_config_container"
#                 ),
#                 rx.flex(
#                     add_column_dialog(),
#                     rx.divider(),
#                     remove_column_dialog(),
#                     direction="column",
#                     spacing="4"
#                 ),
#                 direction="row",
#                 spacing="4"
#             ),
#             spacing="6",
#             direction="column"
#         ),
#         rx.spinner(height="100vh")
#     )









from ...pages.agent_config_page import AgentConfigState

class CSVDataState(AgentConfigState):
    """State management for CSV data editing."""
    _working_config: ConfigStoreEntryModelView = \
        ConfigStoreEntryModelView()
    selected_variant: str = "Custom"
    selected_cell: str = ""
    num_rows: int = 10
    table_width: str = "40rem"

    # Computed vars with proper type hints
    @rx.var(cache=True)
    def working_config(self) -> ConfigStoreEntryModelView:
        return next(
            (config for config in self.working_agent.config_store 
             if config.component_id == self.working_agent.selected_config_component_id),
            ConfigStoreEntryModelView()
        )

    @rx.var(cache=True)
    def variants(self) -> Dict[str, Dict[str, List[str]]]:
        return self.working_config.csv_variants

    @rx.var(cache=True)
    def working_headers(self) -> List[str]:
        logger.debug(f"variant: {self.selected_variant}\nkeys: {list(self.working_config.csv_variants[self.selected_variant].keys())}")
        return list(self.working_config.csv_variants[self.selected_variant].keys())

    @rx.var(cache=True)
    def working_rows(self) -> List[List[str]]:
        working_dict = self.working_config.csv_variants[self.selected_variant]
        headers = list(working_dict.keys())
        return [[working_dict[header][i] for header in headers] 
                for i in range(self.num_rows)]

    # Event handlers
    @rx.event
    def double_click_event(self, cell_uid: str):
        """Handle double click on a cell."""
        self.selected_cell = cell_uid

    @rx.event
    def lose_cell_focus(self):
        """Clear cell selection."""
        self.selected_cell = ""

    @rx.event
    def set_variant(self, variant: str):
        """Switch between variants."""
        self.selected_variant = variant

    @rx.event
    def update_cell(self, cell_uid: str, header: str, changes: str, index: int = None, row_idx: int = None, is_row_cell: bool = False):
        """Update cell content."""
        if is_row_cell:
            self.working_config.csv_variants[self.selected_variant][header][row_idx] = changes
        else:
            # Update header name
            new_dict = {}
            for key in self.working_headers:
                v = list(self.working_config.csv_variants[self.selected_variant][key])
                if key == header:
                    new_dict[changes] = v
                else:
                    new_dict[key] = v
            self.working_config.csv_variants[self.selected_variant] = new_dict
        yield CSVDataState.force_rerender

    @rx.event
    def add_column(self, form_data: dict):
        """Add a new column."""
        column_name = form_data["column_name"]
        self.working_config.csv_variants[self.selected_variant][column_name] = [""] * self.num_rows
        yield rx.toast.info(f"Added column: {column_name}", position="bottom-right")
        yield CSVDataState.force_rerender

    @rx.event
    def force_rerender(self):
        logger.debug("bro is not going back home x3")
        yield
        if self.selected_variant == "Custom":
            self.selected_variant="Default 1"
            self.selected_variant="Custom"
        else:
            safe = self.selected_variant.copy()
            self.selected_variant="Custom"
            self.selected_variant=safe

    @rx.event
    def remove_column(self, form_data: dict):
        """Remove a column."""
        column_name = form_data["column_name"]
        del self.working_config.csv_variants[self.selected_variant][column_name]
        yield rx.toast.info(f"Removed column: {column_name}", position="bottom-right")
        yield CSVDataState.force_rerender

# Components
def craft_table_cell(content: str, header: str = None, index: int = None, row_idx: int = None, header_cell: bool = False):
    """Create a table cell component."""
    cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
    cell_uid = f"{CSVDataState.selected_variant}-template-cell-{header}-{index}-{row_idx}-header?-{header_cell}"
    
    return cell_component(
        rx.box(
            rx.cond(
                CSVDataState.selected_cell == cell_uid,
                rx.text_field(
                    # id=cell_uid,
                    value=content,
                    on_blur=CSVDataState.lose_cell_focus,
                    autofocus=True,
                    on_change=lambda changes: CSVDataState.update_cell(cell_uid, header, changes, index, row_idx, not header_cell)
                ),
                rx.text(
                    content,
                    id=cell_uid
                    )
            ),
        ),
        class_name="csv_data_cell",
        on_double_click=lambda: CSVDataState.double_click_event(cell_uid)
    )

def csv_table():
    """Create the main table component."""
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
    """Dialog for adding a new column."""
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
    """Dialog for removing a column."""
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

def csv_data_field():
    """Main CSV data field component."""

    return rx.cond(
        CSVDataState.is_hydrated, 
        rx.flex(
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
            direction="column"
        ),
        rx.spinner(height="100vh")
    )
