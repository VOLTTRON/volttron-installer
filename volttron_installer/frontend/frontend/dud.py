import reflex as rx

class DeleteState(rx.State):
    items: list[dict] = [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item 2"},
        {"id": 3, "name": "Item 3"},
    ]

    def delete_item(self, item_id: int):
        self.items = [item for item in self.items if item["id"] != item_id]

def index():
    return rx.vstack(
        rx.foreach(
            DeleteState.items,
            lambda item: rx.hstack(
                rx.text(item["name"]),
                rx.button(
                    "Delete",
                    color_scheme="red",
                    on_click=lambda: DeleteState.delete_item(item["id"])
                ),
                spacing="3",
            )
        ),
        spacing="4"
    )