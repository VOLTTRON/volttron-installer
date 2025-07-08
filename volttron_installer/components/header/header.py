import reflex as rx 

def header(*children, **props) -> rx.Component:
    return rx.flex( 
        *children,
        **props,
        spacing="6",
        direction="row",
        padding="1rem",
        align="center",
    )