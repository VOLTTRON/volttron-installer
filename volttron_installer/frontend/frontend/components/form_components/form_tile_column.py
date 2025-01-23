import reflex as rx

def form_tile_column_wrapper( *children ) -> rx.Component:
    
    return rx.container(
        rx.vstack(
            *children
        ),
        padding=".75rem .75rem"
    )