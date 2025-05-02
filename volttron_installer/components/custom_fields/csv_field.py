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
        self.working_config.selected_variant = variant

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
        
        # Ensure that the selected variant change is pushed through into working_config_store_agent
        for config in self.working_agent.config_store:
            if config.component_id == self.working_agent.selected_config_component_id:
                logger.debug(f"Updating config store entry: {config.component_id}")
                config.csv_variants = self.working_config.csv_variants
                break
        yield CSVDataState.force_rerender
        return

    @rx.event
    def add_column(self, form_data: dict):
        """Add a new column."""
        column_name = form_data["column_name"]
        working_variant_copy = self.working_config.csv_variants[self.selected_variant]
        working_variant_copy[column_name] = [""] * self.num_rows
        # Ensure that the selected variant change is pushed through into working_config_store
        self.working_config.csv_variants[self.selected_variant] = working_variant_copy
        
        # Update the config_store entry (add this part)
        for config in self.working_agent.config_store:
            if config.component_id == self.working_agent.selected_config_component_id:
                logger.debug(f"Updating config store entry after adding column: {config.component_id}")
                config.csv_variants = self.working_config.csv_variants
                break
        
        yield rx.toast.info(f"Added column: {column_name}", position="bottom-right")
        yield CSVDataState.force_rerender
        return

    @rx.event
    def force_rerender(self):
        logger.debug("bro is not going back home x3")
        yield
        if self.selected_variant == "Custom":
            self.selected_variant = "Default 1"
            self.selected_variant = "Custom"
            self.working_config.selected_variant = "Custom"
        else:
            safe = self.selected_variant
            self.selected_variant = "Custom"
            self.selected_variant = safe
            self.working_config.selected_variant = safe

    @rx.event
    def remove_column(self, form_data: dict):
        """Remove a column."""
        column_name = form_data["column_name"]
        working_variant_copy = self.working_config.csv_variants[self.selected_variant]
        del working_variant_copy[column_name]
        # Ensure that the selected variant change is pushed through into working_config_store
        self.working_config.csv_variants[self.selected_variant] = working_variant_copy
        
        # Update the config_store entry (add this part)
        for config in self.working_agent.config_store:
            if config.component_id == self.working_agent.selected_config_component_id:
                logger.debug(f"Updating config store entry after removing column: {config.component_id}")
                config.csv_variants = self.working_config.csv_variants
                break
        
        yield rx.toast.info(f"Removed column: {column_name}", position="bottom-right")
        yield CSVDataState.force_rerender
        return
    
# Components
def base_component_wrapper(func_or_disabled=False):
    # If we're called directly with the function
    if callable(func_or_disabled):
        # This is the function case like @base_component_wrapper
        def wrapped(*args, **kwargs):
            return func_or_disabled(*args, **kwargs)
        return wrapped
    
    # This is the parameterized case like @base_component_wrapper(disabled=False)
    disabled = func_or_disabled
    def wrapper(component_func):
        def wrapped(*args, **kwargs):
            # Remove disabled from kwargs if it exists to avoid duplicate
            kwargs.pop('disabled', None)
            # Add the wrapper's disabled value
            kwargs['disabled'] = disabled
            return component_func(*args, **kwargs)
        return wrapped
    return wrapper

@base_component_wrapper
def craft_table_cell(content: str, header: str = None, index: int = None, row_idx: int = None, header_cell: bool = False, disabled: bool = False):
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
                    on_change=lambda changes: CSVDataState.update_cell(cell_uid, header, changes, index, row_idx, not header_cell),
                    disabled=disabled
                ),
                rx.text(
                    content,
                    id=cell_uid
                )
            ),
        ),
        class_name="csv_data_cell",
        on_double_click=lambda: None if disabled else CSVDataState.double_click_event(cell_uid)
    )

@base_component_wrapper
def csv_table(width=r"100%", height="100%", **props):
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

@base_component_wrapper
def add_column_dialog(disabled: bool = False):
    return rx.dialog.root(
        rx.dialog.trigger(
            add_icon_button.add_icon_button(
                tool_tip_content="Add a new column",
                disabled=disabled
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
                            required=True,
                            disabled=disabled
                        ),
                        required_entry=True
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button(
                                "Cancel",
                                variant="soft",
                                disabled=disabled
                            )
                        ),
                        rx.dialog.close(
                            rx.button(
                                "Add",
                                type="submit",
                                disabled=disabled
                            )
                        ),
                        spacing="3",
                        justify="end"
                    ),
                    direction="column",
                    spacing="6"
                ),
                on_submit=CSVDataState.add_column if not disabled else None,
                reset_on_submit=False,
            ),
            max_width="450px",
        )
    )

@base_component_wrapper
def remove_column_dialog(disabled: bool = False):
    return rx.dialog.root(
        rx.dialog.trigger(
            icon_button_wrapper.icon_button_wrapper(
                tool_tip_content="Remove a column",
                icon_key="minus",
                disabled=disabled
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
                            required=True,
                            disabled=disabled
                        ),
                        required_entry=True
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button(
                                "Cancel",
                                variant="soft",
                                disabled=disabled
                            )
                        ),
                        rx.dialog.close(
                            rx.button(
                                "Remove",
                                color_scheme="red",
                                type="submit",
                                disabled=disabled
                            )
                        ),
                        spacing="3",
                        justify="end"
                    ),
                    direction="column",
                    spacing="6"
                ),
                on_submit=CSVDataState.remove_column if not disabled else None,
                reset_on_submit=False,
            ),
            max_width="450px",
        )
    )

def csv_data_field(disabled: bool = False, **props):
    return rx.cond(
        CSVDataState.is_hydrated, 
        rx.flex(
            rx.box(
                rx.select(
                    CSVDataState.variants.keys(),
                    value=CSVDataState.selected_variant,
                    on_change=CSVDataState.set_variant,
                    variant="surface",
                    disabled=disabled
                )
            ),
            rx.flex(
                rx.el.div(
                    csv_table(disabled=disabled, **props),
                    class_name="config_template_config_container"
                ),
                rx.flex(
                    add_column_dialog(disabled=disabled),
                    rx.divider(),
                    remove_column_dialog(disabled=disabled),
                    direction="column",
                    spacing="4"
                ),
                direction="row",
                spacing="4",
                width=r"calc(100% - 2rem)",
                max_width="100%"
            ),
            spacing="6",
            direction="column"
        ),
        rx.spinner(height="100vh")
    )

def simple_table(headers: list, rows: list, width="40rem", height="25rem", **props):
    """
    A simple table component that displays data without editing functionality.
    
    Args:
        headers: List of column headers
        rows: 2D list of row data
        width: Table width (default: "40rem")
        height: Table height (default: "25rem")
        **props: Additional props to pass to the table
        
    Returns:
        A Reflex table component
    """
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.foreach(
                    headers,
                    lambda header, index: rx.table.column_header_cell(
                        rx.text(header),
                        class_name="simple-table-header-cell"
                    )
                )
            )
        ),
        rx.table.body(
            rx.foreach(
                rows,
                lambda row, i: rx.table.row(
                    rx.foreach(
                        row,
                        lambda value, index: rx.table.cell(
                            rx.text(value),
                            class_name="simple-table-cell"
                        )
                    )
                )
            )
        ),
        width=width,
        height=height,
        **props
    )