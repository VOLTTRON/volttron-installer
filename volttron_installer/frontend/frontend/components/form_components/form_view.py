import reflex as rx

def form_view_wrapper( content: list[rx.Component] ) -> rx.Component:
    
    return rx.container(
        rx.flex(
            *[content],
            spacing="6",
            direction="column"
        ),
        padding=".75rem"
    )