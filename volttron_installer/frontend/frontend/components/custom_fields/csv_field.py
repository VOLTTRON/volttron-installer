import typing
import reflex as rx
from ..buttons import add_icon_button, icon_button_wrapper
from ..form_components import form_entry
import asyncio

class TableVariant(rx.Base):
    """Model for both default, and new variants"""
    headers: list[str]
    rows: list[dict[str, str]]


class TableColumns(rx.Base):
    """Model for table columns."""
    columns: dict[str, list[str]]
    row_indices: list[int]  # Store row indices as state

class CSVDataField(rx.ComponentState):
    # Initialize state variables
    data: str = ""
    _selected_variant: str = "Default 1"  # Internal state
    num_rows: int = 10
    
    # Static vars
    variants: dict[str, dict[str, list[str]]] = {
        "Default 1" : {
            "Reference Point Name": ["default 1"]*10,
            "Volttron Point Name": [""]*10,
            "Units": [""]*10,
            "Units Details": [""]*10,
            "Modbus Register": [""]*10,
            "Writable": [""]*10,
            "Point Address": [""]*10,
            "Default Value": [""]*10,
            "Notes": [""]*10,
        },
        "Default 2": {
            "Point Name": [""]*10,
            "Volttron Point Name": [""]*10,
            "Units": [""]*10,
            "Unit Details": [""]*10,
            "BACnet Object Type": [""]*10,
            "Property": [""]*10,
            "Writable": ["f"]*10,
            "Index": [""]*10,
            "Notes" : [""]*10,
        }
    }

    variants3: dict[str, TableColumns] = {
        "Default 1": TableColumns(
            columns={
                "Reference Point Name": ["default 1"] * num_rows,
                "Volttron Point Name": [""] * num_rows,
                "Units": [""] * num_rows,
                "Units Details": [""] * num_rows,
                "Modbus Register": [""] * num_rows,
                "Writable": [""] * num_rows,
                "Point Address": [""] * num_rows,
                "Default Value": [""] * num_rows,
                "Notes": [""] * num_rows,
            },
            row_indices = list(range(num_rows))
        ),
        "Default 2": TableColumns(
            columns={
                "Point Name": [""] * num_rows,
                "Volttron Point Name": [""] * num_rows,
                "Units": [""] * num_rows,
                "Unit Details": [""] * num_rows,
                "BACnet Object Type": [""] * num_rows,
                "Property": [""] * num_rows,
                "Writable": ["f"] * num_rows,
                "Index": [""] * num_rows,
                "Notes": [""] * num_rows,
            },
            row_indices = list(range(num_rows))
        )
    }

    selected_cell: str = ""

    variant_selections: list[str] = list(variants.keys())

    # Reactive vars
    @rx.var(cache=True)
    def working_dict_headers(self) -> list[str]:
        return list(self.variants[self.selected_variant].keys())

    @rx.var(cache=True)
    def working_dict_rows(self) -> list[list[str]]:
        # Accessing our dict values horizontally:
        working_dict = self.variants[self._selected_variant]
        headers = list(working_dict.keys())
        
        num_rows = len(list(working_dict.values())[0])
        rows = []
        
        for i in range(num_rows):
            row = [working_dict[header][i] for header in headers]
            rows.append(row)
            
        return rows

    # ============ working with vars3 ============
    @rx.var(cache=True)
    def working_variant(self) -> TableColumns:
        return self.variants3[self.selected_variant]

    @rx.var(cache=True)
    def working_variant_columns(self) -> list[str]:
        return list(self.variants3[self.selected_variant].columns.keys())

    # ============ end of vars 3 ============

    @rx.var(cache=True)
    def selected_variant(self) -> str:
        return self._selected_variant

    @rx.var(cache=True)
    def working_dict(self) -> dict:
        return self.variants[self._selected_variant]


    # Event handlers
    @rx.event
    def double_click_event(self, cell_uid: str):
        print("cell has been double clicked and we got ", cell_uid)
        self.selected_cell = cell_uid


    @rx.event
    def lose_cell_focus(self, cell_uid: str):
        self.selected_cell = ""

    @rx.event
    def set_select_value(self, value: str):
        self._selected_variant = value

    @rx.event
    def on_add_column(self, info: dict):
        column_name = info["column_name"]
        self.working_variant.columns[column_name] = [""] * self.num_rows
        return rx.toast.info(
            f"Added column: {column_name}",
            position="bottom-right"
        )
   
    @rx.event
    def on_remove_column(self, info: dict):
        column_name = info["column_name"]
        del self.working_variant.columns[column_name]
        return rx.toast.info(
            f"Removed column: {column_name}",
            position="bottom-right"
        )
    
    @rx.event
    async def update_cell(self, header: str, changes: str, index: int, is_row_cell: bool = False):
        """Update cell content with proper state management."""
        value = changes
        
        if is_row_cell:
            # Create a new copy of the columns to trigger state update
            new_columns = dict(self.working_variant.columns)
            new_columns[header][index] = value
            self.working_variant.columns = new_columns
        else:
            new_dict = {}
            for key in list(self.working_variant.columns.keys()):
                v = list(self.working_variant.columns[key])  # Create new list copy
                if key == header:
                    new_dict[value] = v
                else:
                    new_dict[key] = v
                    
            self.working_variant.columns = new_dict
        
        # Force a UI update
        yield

        # Optional: Add debugging after yield
        print(f"Updated value: {value}")
        print(f"Current columns state:\n{self.working_variant.columns}\n")

    # Table creation methods
    @classmethod
    def craft_table_cell(self, content: str, index: int, header: str, header_cell: bool = False):
        cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
        cell_uid = f"{self.selected_variant}-template-cell-{header}-{index}-header?-{header_cell}"

        return cell_component(
            rx.box(
                rx.cond(
                    self.selected_cell == cell_uid,
                    rx.input(
                        value=content,
                        auto_focus=True,
                        on_change=lambda changes: self.update_cell(header, changes, index, not header_cell),
                    ),
                    rx.text(content)
                ),
            ),
            class_name="csv_data_cell",
            on_blur=lambda: self.lose_cell_focus(cell_uid),
            on_double_click= lambda: self.double_click_event(cell_uid)
        )
    
    @classmethod
    def craft_table_row(self, row: list[str]):
        return rx.table.row(
            rx.foreach(
                row,
                lambda value: self.craft_table_cell(rx.text(value))
            )
        )

    @classmethod
    def get_component(cls, data: str = None, **props) -> rx.Component:
        
        return rx.flex(
            # Select dropdown
            rx.box(            
                rx.select(
                    cls.variant_selections,
                    value=cls.selected_variant,
                    on_change=cls.set_select_value,
                    variant="surface",
                )
            ),
            # Table and buttons container
            rx.flex(
                rx.el.div(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.foreach(
                                    cls.working_variant_columns,
                                    lambda _header, _index: cls.craft_table_cell(content=_header, header=_header, index=_index, header_cell=True)
                                )
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                cls.working_variant.row_indices,
                                lambda row_index: rx.table.row(
                                    rx.foreach(
                                        cls.working_variant_columns,
                                        lambda header: cls.craft_table_cell(
                                            content=cls.working_variant.columns[header][row_index],
                                            header=header,
                                            index=row_index,
                                        )
                                    )
                                )

                        # ==============================================
                                # cls.working_variant_rows,
                                # lambda row, index: rx.table.row(
                                #     rx.foreach(
                                #         cls.working_variant_headers,
                                #         lambda header: rx.table.cell(
                                #             rx.text(row[header]),
                                #             class_name="csv_data_cell",
                                #             on_double_click=cls.double_click_event
                                #         )
                                #     )
                                # )
                        # ==============================================
                                # cls.working_dict_rows,
                                # lambda row: cls.craft_table_row(row)
                            )
                        ),
                        width="40rem",
                        height="25rem",
                    ),
                    class_name="config_template_config_container"
                ),
                # Container for dialog trigger buttons
                rx.flex(
                    rx.dialog.root(
                        rx.dialog.trigger(
                            # rx.button(rx.icon("plus", size=30), variant="soft")
                            add_icon_button.add_icon_button(
                                tool_tip_content="Add a new column"
                            ),
                        ),
                        rx.dialog.content(
                            rx.dialog.title(
                                "Add a new column"
                            ),
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
                                on_submit=cls.on_add_column,
                                reset_on_submit=False,
                            ),
                            max_width="450px",
                        )
                    ),
                    rx.dialog.root(
                        rx.dialog.trigger(
                            icon_button_wrapper.icon_button_wrapper(
                                tool_tip_content="Remove a column",
                                icon_key="minus"
                            ),
                        ),
                        rx.dialog.content(
                            rx.dialog.title(
                                "Remove a column"
                            ),
                            rx.form(
                                rx.flex(
                                    form_entry.form_entry(
                                        "Column Name",
                                        rx.select(
                                            cls.working_variant_columns,
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
                                on_submit=cls.on_remove_column,
                                reset_on_submit=False,
                            ),
                            max_width="450px",
                        )
                    ),
                    direction="column",
                    spacing="4"
                ),
                direction="row",
                spacing="4"
            ),
            spacing="6",
            direction="column"
        )

    def retrieve_data(self):
        # Convert cell content into csv
        pass

# Create component instance
csv_data_field = CSVDataField.create


# This is a solution ive been trying to play with, not really working so i've decided to commit a working state
"""
import typing
import reflex as rx
from ..buttons import add_icon_button, icon_button_wrapper
from ..form_components import form_entry

# class TableColumns(rx.Base):
#     columns: dict[str, list[str]]
#     row_indices: list[int]  # Store row indices as state

    # variants3: dict[str, TableColumns] = {
    #     "Default 1": TableColumns(
    #         columns={
    #             "Reference Point Name": ["default 1"] * num_rows,
    #             "Volttron Point Name": [""] * num_rows,
    #             "Units": [""] * num_rows,
    #             "Units Details": [""] * num_rows,
    #             "Modbus Register": [""] * num_rows,
    #             "Writable": [""] * num_rows,
    #             "Point Address": [""] * num_rows,
    #             "Default Value": [""] * num_rows,
    #             "Notes": [""] * num_rows,
    #         },
    #         row_indices = list(range(num_rows))
    #     ),
    #     "Default 2": TableColumns(
    #         columns={
    #             "Point Name": [""] * num_rows,
    #             "Volttron Point Name": [""] * num_rows,
    #             "Units": [""] * num_rows,
    #             "Unit Details": [""] * num_rows,
    #             "BACnet Object Type": [""] * num_rows,
    #             "Property": [""] * num_rows,
    #             "Writable": ["f"] * num_rows,
    #             "Index": [""] * num_rows,
    #             "Notes": [""] * num_rows,
    #         },
    #         row_indices = list(range(num_rows))
    #     )
    # }


class CSVDataField(rx.ComponentState):
    data: str = ""
    _selected_variant: str = "Default 1"  # Internal state
    num_rows: int = 10
    _row_iter: list[int] = list(range(num_rows))
    
    variants: dict[str, dict[str, list[str]]] = {
        "Default 1" : {
            "Reference Point Name": ["default 1"]*num_rows,
            "Volttron Point Name": [""]*num_rows,
            "Units": [""]*num_rows,
            "Units Details": [""]*num_rows,
            "Modbus Register": [""]*num_rows,
            "Writable": [""]*num_rows,
            "Point Address": [""]*num_rows,
            "Default Value": [""]*num_rows,
            "Notes": [""]*num_rows,
        },
        "Default 2": {
            "Point Name": [""]*num_rows,
            "Volttron Point Name": [""]*num_rows,
            "Units": [""]*num_rows,
            "Unit Details": [""]*num_rows,
            "BACnet Object Type": [""]*num_rows,
            "Property": [""]*num_rows,
            "Writable": ["f"]*num_rows,
            "Index": [""]*num_rows,
            "Notes" : [""]*num_rows,
        }
    }

    selected_cell: str = ""

    variant_selections: list[str] = list(variants.keys())

    # Reactive vars
    @rx.var(cache=True)
    def working_dict_headers(self) -> list[str]:
        return list(self.variants[self.selected_variant].keys())

    @rx.var(cache=True)
    def variant_selections(self) -> list[str]: return list(self.variants.keys())

    @rx.var(cache=True)
    def working_dict_rows(self) -> list[list[str]]:
        # Accessing our dict values horizontally:
        working_dict = self.variants[self._selected_variant]
        headers = list(working_dict.keys())
        
        num_rows = len(list(working_dict.values())[0])
        rows = []
        
        for i in range(num_rows):
            row = [working_dict[header][i] for header in headers]
            rows.append(row)
            
        return rows

    @rx.var(cache=True)
    def selected_variant(self) -> str:
        return self._selected_variant

    @rx.var(cache=True)
    def working_dict(self) -> dict[str, list[str]]: return self.variants[self.selected_variant]

    # Event handlers
    @rx.event
    def double_click_event(self, cell_uid: str):
        print("cell has been double clicked and we got ", cell_uid)
        self.selected_cell = cell_uid

    @rx.event
    def lose_cell_focus(self, cell_uid: str):
        self.selected_cell = ""

    @rx.event
    def set_select_value(self, value: str):
        self._selected_variant = value

    @rx.event
    def on_add_column(self, info: dict):
        column_name = info["column_name"]
        self.working_dict[column_name] = [""] * self.num_rows
        return rx.toast.info(
            f"Added column: {column_name}",
            position="bottom-right"
        )
   
    @rx.event
    def on_remove_column(self, info: dict):
        column_name = info["column_name"]
        del self.working_dict[column_name]
        return rx.toast.info(
            f"Removed column: {column_name}",
            position="bottom-right"
        )
    
    @rx.event
    def update_cell(self, header: str, changes: str, index: int = None, is_row_cell: bool = False):
        value = changes
        
        if is_row_cell:
            self.working_dict[header][index] = value
        else:
            pass
            # new_dict = {}
            # for key in list(self.working_variant.columns.keys()):
            #     v = list(self.working_variant.columns[key])  # Create new list copy
            #     if key == header:
            #         new_dict[value] = v
            #     else:
            #         new_dict[key] = v
                    
    
        # Optional: Add debugging after yield
        print(f"Updated value: {value}")
        # print(f"Current columns state:\n{self.working_variant.columns}\n")

    # Table creation methods
    @classmethod
    def craft_table_cell(self, content: str, header: str, index: int = False, header_cell: bool = False):
        cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
        cell_uid = f"{self.selected_variant}-template-cell-{header}-{str(index)}-header?-{str(header_cell)}"

        return cell_component(
            rx.box(
                rx.cond(
                    self.selected_cell == cell_uid,
                    rx.input(
                        value=content,
                        on_change=lambda changes: self.update_cell(header, changes, index, not header_cell),
                    ),
                    rx.text(content)
                ),
            ),
            class_name="csv_data_cell",
            on_blur=lambda: self.lose_cell_focus(cell_uid),
            on_double_click= lambda: self.double_click_event(cell_uid)
        )

    @classmethod
    def craft_simple_cell(self, content) -> rx.Component:
        return rx.table.cell(content)


    @classmethod
    def craft_table_row(self, row: list[str], outer_index=False):
        return rx.table.row(
            rx.foreach(
                row,
                lambda value: self.craft_table_cell(
                    value, 
                    header=self.working_dict_headers[index],
                    index=index
                )
            )
        )

    @classmethod
    def get_component(cls, data: str = None, **props) -> rx.Component:
        
        return rx.flex(
            # Select dropdown
            rx.box(            
                rx.select(
                    cls.variant_selections,
                    value=cls.selected_variant,
                    on_change=cls.set_select_value,
                    variant="surface",
                )
            ),
            # Table and buttons container
            rx.flex(
                rx.el.div(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.foreach(
                                    cls.working_dict_headers,
                                    lambda _header: cls.craft_table_cell(content=_header, header=_header, header_cell=True)
                                )
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                # cls._row_iter,
                                # lambda row_index: rx.table.row(
                                #     rx.foreach(
                                #         cls.working_dict_headers,
                                #         lambda header: cls.craft_table_cell(
                                #             content=cls.working_dict[header][row_index],
                                #             header=header,
                                #             index=row_index,
                                #         )
                                #     )
                                # )
                                cls.working_dict_rows,
                                lambda row: rx.table.row(
                                    rx.foreach(
                                        row,
                                        lambda item: rx.table.cell(item)
                                    )
                                )
                                # lambda row, out_index: cls.craft_table_row(row, out_index)
                            )
                        ),
                        width="40rem",
                        height="25rem",
                    ),
                    class_name="config_template_config_container"
                ),
                # Container for dialog trigger buttons
                rx.flex(
                    rx.dialog.root(
                        rx.dialog.trigger(
                            # rx.button(rx.icon("plus", size=30), variant="soft")
                            add_icon_button.add_icon_button(
                                tool_tip_content="Add a new column"
                            ),
                        ),
                        rx.dialog.content(
                            rx.dialog.title(
                                "Add a new column"
                            ),
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
                                on_submit=cls.on_add_column,
                                reset_on_submit=False,
                            ),
                            max_width="450px",
                        )
                    ),
                    rx.dialog.root(
                        rx.dialog.trigger(
                            icon_button_wrapper.icon_button_wrapper(
                                tool_tip_content="Remove a column",
                                icon_key="minus"
                            ),
                        ),
                        rx.dialog.content(
                            rx.dialog.title(
                                "Remove a column"
                            ),
                            rx.form(
                                rx.flex(
                                    form_entry.form_entry(
                                        "Column Name",
                                        rx.select(
                                            cls.working_dict_headers,
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
                                on_submit=cls.on_remove_column,
                                reset_on_submit=False,
                            ),
                            max_width="450px",
                        )
                    ),
                    direction="column",
                    spacing="4"
                ),
                direction="row",
                spacing="4"
            ),
            spacing="6",
            direction="column"
        )

    def retrieve_data(self):
        # Convert cell content into csv
        pass

# Create component instance
csv_data_field = CSVDataField.create
"""