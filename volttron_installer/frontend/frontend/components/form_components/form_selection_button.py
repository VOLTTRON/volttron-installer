import reflex as rx

def form_selection_button(
    selected_item: rx.Var[str] = "_",
    selection_id: str = "",
    text: str = "",
    spacing="2",
    delete_component: bool | rx.Component = False,
    **props
) -> rx.Component:
    
    return rx.hstack(
        rx.flex(
            rx.text(text),
            class_name="form_selection_button",
            style={
                "background_color": rx.cond(
                    selected_item == selection_id,
                    "#3C3C3E",
                    "#2A2A2C"
                ),
                "_hover": {
                    "background_color" : rx.cond(
                        selected_item == selection_id,
                        "#444446",
                        "#333335"
                    )
                }
            },
            **props
        ),
        rx.cond(
            delete_component==False,
            rx.flex(
                rx.text("delete"),
                align="center",
                justify="center",
            ),
            rx.flex(        
                delete_component,
                align="center",
                justify="center"
            )
        ),  
        spacing=spacing,
        align="center",
    )