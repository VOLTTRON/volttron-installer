import reflex as rx
from ..buttons import add_icon_button, icon_button_wrapper
from ..form_components import form_entry
from typing import Dict, List, Optional
from ...model_views import ConfigStoreEntryModelView
from loguru import logger
#version 1
from ..form_components import form_entry
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

def csv_table(width="40rem", height="25rem", **props):
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
        width=width,
        height=height,
        **props
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

def csv_data_field(**props):
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
                    csv_table(**props),
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
