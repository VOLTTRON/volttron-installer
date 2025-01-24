import reflex as rx 

def header(*children, **props) -> rx.Component:
    return rx.flex( 
        *children,
        **props,
        align="start",
        spacing="6",
        direction="row",
        padding="1rem"
    )