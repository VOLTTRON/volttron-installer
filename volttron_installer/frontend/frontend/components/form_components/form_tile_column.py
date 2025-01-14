import reflex as rx

def form_tile_column_wrapper( content: rx.Component ) -> rx.Component:
    
    return rx.container(
        rx.vstack(
            content
        ),
        padding=".75rem .75rem"
        # padding="2rem"+\
    )