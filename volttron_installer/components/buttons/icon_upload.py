import reflex as rx


def icon_upload(text: str = "Upload File", **props ) -> rx.Component:
    return rx.hstack(
        rx.icon("upload"),
        rx.text(text),
        spacing="3",
        user_select="none",
        padding=".25rem",
        border_radius=".5rem",
        cursor="pointer",
        style = {
            "_hover" : {
                "background-color" : "#2A2A2C"
            }
        },
        **props
    )
