import reflex as rx

def delete_icon_button(width="1.5rem", height="1.5rem", **props) -> rx.Component:
    return rx.flex(
        rx.icon("trash-2", size=15),
        # width=width,
        # height=height,
        style={
            "_hover": {
                "background" : "red"
            }
        },
        class_name="icon_button",
        direction="column",
        justify="center",
        align="center",
        **props
    )