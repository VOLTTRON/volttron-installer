import reflex as rx

class State(rx.State):
    selected_div: str = ""  # Store selected div id

    def select_div(self, div_id: str):
        print("im being activated")
        self.selected_div = div_id

def create_div(id: str, content: str) -> rx.Component:
    return rx.el.div(
        content,
        id=id,
        padding="1em",
        border="1px solid #ccc",
        cursor="pointer",
        background_color=rx.cond(State.selected_div == id, "blue", "orange"),
        _hover={"background_color": "#f5f5f5"},
        on_click=lambda: State.select_div(id)
    )

def index():
    return rx.el.div(
        rx.hstack(
            create_div("div1", "Option 1"),
            create_div("div2", "Option 2"),
            create_div("div3", "Option 3"),
            spacing="4",
        ),
    )
