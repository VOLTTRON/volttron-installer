import reflex as rx

def form_view_wrapper(*children, **props) -> rx.Component:
    
    return rx.container(
        rx.flex(
            *children,
            **props,
            spacing="6",
            direction="column"
        ),
        padding=".75rem"
    )