import reflex as rx

def add_icon_button(
        hover_color: str ="#2A2A2C", 
        tool_tip_content: str | bool = False, 
        size: int =30, 
        **props
        ) -> rx.Component:
    button = rx.box(
        rx.flex(
            rx.icon("plus", size=size),
            style={
                "_hover": {
                    "background": hover_color
                }
            },
            class_name="icon_button",
            direction="column",
            justify="center",
            align="center",
            **props
        )
    )
    
    if tool_tip_content:
        return rx.box(  # Wrap the tooltip in a box
            rx.tooltip(
                button,
                content=tool_tip_content,
                side="bottom",
                align="center"
            )
        )
    return rx.box(button)  # Wrap the button in a box