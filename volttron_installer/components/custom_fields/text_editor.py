import reflex as rx


def text_editor(height="25rem", width="40rem", size="3", placeholder="Type out JSON or upload a file!", **props):
    return rx.text_area(
        width=width,
        height=height,
        size=size,
        spell_check="false",
        placeholder=placeholder,
        class_name="text_editor",
        **props
    )
