import reflex as rx
from reflex_ag_grid import ag_grid
import pandas as pd
import os

class EditableGridComponent(rx.ComponentState):
    data: list[dict] = []
    all_columns: list = []
    two_columns: list = []
    column_defs: list = []
    n_clicks = 0

    @rx.event
    def init_columns(self):
        self.all_columns = [
            ag_grid.column_def(field="country"),
            ag_grid.column_def(field="pop"),
            ag_grid.column_def(field="continent"),
            ag_grid.column_def(field="lifeExp"),
            ag_grid.column_def(field="gdpPercap"),
        ]
        self.two_columns = [
            ag_grid.column_def(field="country"),
            ag_grid.column_def(field="pop"),
        ]
        self.column_defs = self.all_columns
    
    @rx.event
    def update_columns(self):
        self.n_clicks += 1
        if self.n_clicks % 2 != 0:
            self.column_defs = self.two_columns
        else:
            self.column_defs = self.all_columns

    @rx.event
    def load_data(self):
        _df = pd.read_csv(
            "https://raw.githubusercontent.com/plotly/datasets/master/gapminder2007.csv"
        )
        self.data = _df.to_dict("records")

    @rx.event
    def cell_value_changed(self, row, col_field, new_value):
        self._data_df.at[row, col_field] = new_value
        self.data = self._data_df.to_dict("records")

    @classmethod
    def get_component(cls, **props):
        return rx.vstack(
            rx.button(
                "Toggle Columns",
                on_click=cls.update_columns,
            ),
            ag_grid(
                id="ag_grid_basic_editing",
                row_data=cls.data,
                column_defs=cls.column_defs,
                on_cell_value_changed=cls.cell_value_changed,
                on_mount=cls.init_columns,
                width="40rem",
                height="40vh",
                **props
            ),
        )

# Create the component
editable_grid = EditableGridComponent.create

current_dir = os.path.dirname(__file__)
blank_csv_file_path = os.path.join(current_dir, "blank_100.csv")

df = pd.read_csv(blank_csv_file_path)
class AGGridEditingState(rx.State):
    data: list[dict] = [{"col"+str(i): "" for i in range(10)} for _ in range(10)]

    @rx.event
    def cell_value_changed(self, row, col_field, new_value):
        self._data_df.at[row, col_field] = new_value
        self.data = self._data_df.to_dict("records")

column_defs = [
    ag_grid.column_def(
        field="col"+str(i),
        editable=True, 
        cell_editor=ag_grid.editors.text
    ) for i in range(10)
]

def ag_grid_simple():
    return ag_grid(
        id="ag_grid_basic_editing",
        row_data=AGGridEditingState.data,
        column_defs=column_defs,
        on_cell_value_changed=AGGridEditingState.cell_value_changed,
        width="40rem",
        height="25rem"
    )

class CSVDataField(rx.ComponentState):
    data: str = ""

    