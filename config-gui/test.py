from nicegui import ui
data = [
    {"name": "Alice", "age": 18},
    {"name": "Bob", "age": 21},
    {"name": "Carol", "age": 42},
]

def update_data_from_table_change(e):
    data[e.args["rowIndex"]] = e.args["data"]

table = ui.aggrid({
    "columnDefs": [
        {"field": "name", "editable": True, "sortable": True},
        {"field": "age", "editable": True},
    ],
    "rowData": data,
    "rowSelection": "multiple",
    "stopEditingWhenCellsLoseFocus": True,
}).on("cellValueChanged", update_data_from_table_change)

async def delete_selected():
    selected_rows = await table.get_selected_rows()
    data[:] = [row for row in data if row not in selected_rows]
    table.update()

def new_row():
    data.append({"name": "New default name", "age": None})
    table.update()

ui.button("Delete selected", on_click=delete_selected)
ui.button("New row", on_click=new_row)

ui.label().bind_text_from(globals(), "data", lambda data: f"Current data: {data}")

ui.run()