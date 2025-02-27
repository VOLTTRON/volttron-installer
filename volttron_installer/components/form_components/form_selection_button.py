import reflex as rx

def form_selection_button(
    selected_item: rx.Var[str] = "_",
    selection_id: str = "",
    text: str = "",
    spacing="2",
    delete_component: bool | rx.Component = False,
    uncaught_prop: bool = False,
    **props
) -> rx.Component:
    """
    Params:
    selection_item: The component Id of the component you are creating
    selection_id: The State var that we compare the selection_item to
    """


    return rx.hstack(
        rx.flex(
            rx.text(text),
            class_name=f"form_selection_button {rx.cond(uncaught_prop, 'uncaught', '')}",
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