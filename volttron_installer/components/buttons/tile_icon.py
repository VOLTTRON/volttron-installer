import reflex as rx

def tile_icon(icon="arrow-right", class_name="icon_button", width="1.5rem", height="1.5rem", **props) -> rx.Component:
    return rx.flex(
        rx.icon(icon, size=20),
        # width=width,
        # height=height,
        class_name="icon_button",
        direction="column",
        justify="center",
        align="center",
        **props
    )