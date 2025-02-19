import typing
import reflex as rx
from ..buttons import add_icon_button, icon_button_wrapper
from ..form_components import form_entry
import asyncio

class CSVDataField(rx.ComponentState):
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

    # Reactive vars
    @rx.var(cache=True)
    def working_dict_headers(self) -> list[str]: return list(self.variants[self.selected_variant].keys())

    @rx.var(cache=True)
    def variant_selections(self) -> list[str]: return list(self.variants.keys())

    @rx.var(cache=True)
    def working_dict_rows(self) -> list[list[str]]:
        # Accessing our dict values horizontally:
        working_dict = self.variants[self.selected_variant]
        headers = list(working_dict.keys())
        
        num_rows = len(list(working_dict.values())[0])
        rows = []
        
        for i in range(num_rows):
            row = [working_dict[header][i] for header in headers]
            rows.append(row)
            
        return rows

    @rx.var(cache=True)
    def selected_variant(self) -> str: return self._selected_variant

    @rx.var(cache=True)
    def working_dict(self) -> dict[str, list[str]]: return self.variants[self.selected_variant]

    # Event handlers
    @rx.event
    def double_click_event(self, cell_uid: str):
        print("cell has been double clicked and we got ", cell_uid)
        self.selected_cell = cell_uid

    @rx.event
    def lose_cell_focus(self):
        self.selected_cell = ""

    @rx.event
    def set_select_value(self, value: str):
        self._selected_variant = value

    @rx.event
    def on_add_column(self, info: dict):
        column_name = info["column_name"]
        self.variants[self.selected_variant][column_name] = [""] * self.num_rows
        return rx.toast.info(
            f"Added column: {column_name}",
            position="bottom-right"
        )
   
    @rx.event
    def on_remove_column(self, info: dict):
        column_name = info["column_name"]
        del self.variants[self.selected_variant][column_name]
        return rx.toast.info(
            f"Removed column: {column_name}",
            position="bottom-right"
        )
    
    @rx.event
    def update_cell(self, header: str, changes: str, index: int = None, row_idx: int = None, is_row_cell: bool = False):
        value = changes
        
        if is_row_cell:
            self.variants[self.selected_variant][header][row_idx] = value
        else:
            new_dict = {}
            for key in self.working_dict_headers:
                v = list(self.variants[self.selected_variant][key])  # Create new list copy
                if key == header:
                    new_dict[value] = v
                else:
                    new_dict[key] = v
            self.variants[self.selected_variant] = new_dict
    
        print(f"Updated value: {value}")
        print(f"current headers: {list(self.variants[self.selected_variant].keys())}")

    # Table creation methods
    @classmethod
    def craft_table_cell(self, content: str, header: str = None, index: int = None, row_idx: int = None, header_cell: bool = False):
        cell_component = rx.table.column_header_cell if header_cell else rx.table.cell
        cell_uid = f"{self.selected_variant}-template-cell-{header}-{index}-{row_idx}-header?-{header_cell}"

        return cell_component(
            rx.box(
                rx.cond(
                    self.selected_cell == cell_uid,
                    rx.text_field(
                        value=content,
                        on_blur=lambda: self.lose_cell_focus(),
                        autofocus=True,
                        on_change=lambda changes: self.update_cell(header, changes, index, row_idx, not header_cell)
                    ),
                    rx.text(content)
                ),
            ),
            class_name="csv_data_cell",
            on_double_click= lambda: self.double_click_event(cell_uid)
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
                                    lambda header, index: cls.craft_table_cell(content=header, header=header, index=index, header_cell=True)
                                )
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                cls.working_dict_rows,
                                lambda row, i: rx.table.row(
                                    rx.foreach(
                                        row,
                                        lambda value, index: cls.craft_table_cell(
                                            content=value, 
                                            header=cls.working_dict_headers[index], 
                                            index=index,
                                            row_idx=i
                                        )
                                    )
                                )
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

# Create component instance
csv_data_field = CSVDataField.create


def csv_field(custom_data: str | dict = None) -> rx.Component:
    ...