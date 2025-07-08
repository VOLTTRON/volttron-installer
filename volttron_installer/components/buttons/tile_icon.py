import reflex as rx

def tile_icon(
    icon="arrow-right", 
    class_name="icon_button", 
    width="1.5rem", 
    height="1.5rem", 
    tooltip: str | None = None,
    **props
) -> rx.Component:
    component = rx.box(
        rx.flex(
            rx.icon(icon, size=20),
            class_name=class_name,
            direction="column",
            justify="center", 
            align="center",
            **props
        )
    )
    
    if tooltip:
        return rx.box(
            rx.tooltip(
                component,
                content=tooltip,
                side="top"
            )
        )
    return component