import reflex as rx 

def header(*children, **props) -> rx.Component:
    return rx.flex( 
        rx.hstack(
                *children,
                align="start",
                **props,
                spacing="6"
            ),
        padding="1rem"
    )