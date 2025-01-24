import reflex as rx


def text_editor(**props):
    return rx.text_area(
        width="40rem",
        height="25rem",
        placeholder="Type out JSON or upload a file!",
        **props
    )