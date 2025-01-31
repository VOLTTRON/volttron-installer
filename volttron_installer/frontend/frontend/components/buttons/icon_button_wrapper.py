# like most of the icon buttons, but just a wrapper for consistency
# WIll let you input whatever symbol you want

import reflex as rx

def icon_button_wrapper(
        hover_color: str ="#2A2A2C", 
        tool_tip_content: str | bool = False, 
        size: int =30,
        icon_key: str = "plus",
        **props
        ) -> rx.Component:
    
    button = rx.box(
        rx.flex(
            rx.icon(icon_key, size=size),
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
        return rx.box(
            rx.tooltip(
                button,
                content=tool_tip_content,
                side="bottom",
                align="center"
            )
        )
    
    return button