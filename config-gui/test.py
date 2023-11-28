from nicegui import ui

data = [
    {"col 1": "", "col 2": "", "col 3": ""},
]

columns = [
    {"field": "col 1", "editable": True},
    {"field": "col 2", "editable": True},
    {"field": "col 3", "editable": True},
]

global new_column_start
new_column_start = 4

def update_data_from_table_change(e):
    data[e.args["rowIndex"]] = e.args["data"]

table = ui.aggrid({
    "columnDefs": columns,
    "rowData": data,
    "rowSelection": "multiple",
    "stopEditingWhenCellsLoseFocus": True, 
}).on("cellValueChanged", update_data_from_table_change)

async def delete_selected():
    selected_rows = await table.get_selected_rows()
    data[:] = [row for row in data if row not in selected_rows]
    table.update()

def new_row():
    row_dict = {}
    for col in columns:
        row_dict.update({col["field"]: ""})
    data.append(row_dict)
    table.update()

def new_column():
    global new_column_start
    new_column = {"field": f'col {new_column_start}', "editable": True}
    columns.append(new_column)

    # update rows with new column
    for row in data:
        row.update({f'col {new_column_start}': ""})

    new_column_start += 1
    table.update()

ui.button("Delete selected", on_click=delete_selected)
ui.button("New row", on_click=new_row)
ui.button("New column", on_click=new_column)

ui.label().bind_text_from(globals(), "data", lambda data: f"Current data: {data}")

ui.run()