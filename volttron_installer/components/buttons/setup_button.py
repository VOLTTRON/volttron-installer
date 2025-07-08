import reflex as rx

def setup_button(text: str, **props)->rx.Component:
    return rx.button(
        text,
        variant="soft",
        **props
    )